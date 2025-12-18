import sys
import os
from dotenv import load_dotenv
import glob
import requests
from datetime import datetime
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# --- KHẮC PHỤC LỖI UNICODE TRÊN WINDOWS ---
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

VECTOR_DB_PATH = "rag_chroma_db"
DATA_FOLDER = "data_documents"

# MÔ HÌNH NHÚNG VĂN BẢN
# EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-large"
# EMBEDDING_MODEL_NAME = "vinai/phobert-base"
EMBEDDING_MODEL_NAME = "bkai-foundation-models/vietnamese-bi-encoder"

# Cấu hình chia nhỏ tài liệu
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100
REPORT_FILE = "data_documents/ThongKeKTX.txt"


# --- CẤU HÌNH API (DÙNG CHO BÁO CÁO TỰ ĐỘNG) ---
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME_ENV")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD_ENV")


# ---------------------- Tạo báo cáo -------------------------------
def get_access_token():
    """Mô phỏng đăng nhập để lấy JWT Access Token."""
    print("--- 1. ĐĂNG NHẬP VÀ LẤY TOKEN TỰ ĐỘNG ---")
    login_url = f"{API_BASE_URL}/login"
    try:
        response = requests.post(
            login_url,
            headers={"Content-Type": "application/json"},
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
        )
        response.raise_for_status()

        data = response.json()
        access_token = data.get('access_token')

        if access_token:
            print("✅ Đăng nhập thành công! Đã lấy Access Token.")
            return access_token
        else:
            print("🔴 LỖI: Đăng nhập thành công nhưng không tìm thấy access_token trong phản hồi.")
            return None

    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response is not None else 'Không xác định'
        print(f"🔴 LỖI ĐĂNG NHẬP: Status Code {status_code} - Vui lòng kiểm tra tài khoản và mật khẩu hoặc API URL.")
        return None


def fetch_data(token, endpoint, params=None):
    """Gửi yêu cầu GET đến API Protected."""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            return data.get('data', data)

        return data

    except requests.exceptions.RequestException as e:
        print(f"🔴 Lỗi khi gọi API {endpoint}: {e}")
        return []


def generate_report(token):
    """
    Thu thập dữ liệu và tạo báo cáo KTX.
    Nội dung báo cáo được định dạng tối ưu cho việc chia Chunk.
    """
    if token is None:
        print("🔴 Không thể tạo báo cáo tự động: Không có token truy cập.")
        return False

    print("\n--- 2. BẮT ĐẦU TẠO BÁO CÁO KTX (DỮ LIỆU THỜI GIAN THỰC) ---")
    # 1. THU THẬP DỮ LIỆU
    areas = fetch_data(token, "/api/v1/protected/dorm-areas")
    managers = fetch_data(token, "/api/v1/protected/managers")
    periods = fetch_data(token, "/api/v1/protected/registration-periods")
    applications = fetch_data(token, "/api/v1/protected/dorm-applications")
    contracts = fetch_data(token, "/api/v1/protected/contracts")
    duty_schedules = fetch_data(token, "/api/v1/protected/duty-schedules")

    # Đảm bảo dữ liệu là List
    areas = areas if isinstance(areas, list) else []
    managers = managers if isinstance(managers, list) else []
    periods = periods if isinstance(periods, list) else []
    applications = applications if isinstance(applications, list) else []
    contracts = contracts if isinstance(contracts, list) else []
    duty_schedules = duty_schedules if isinstance(duty_schedules, list) else []

    # 2. XỬ LÝ VÀ THỐNG KÊ
    app_stats = {
        'total': len(applications),
        'pending': sum(1 for app in applications if app.get('status') == 'pending'),
        'approved': sum(1 for app in applications if app.get('status') == 'approved'),
        'rejected': sum(1 for app in applications if app.get('status') == 'rejected'),
    }

    contract_stats = {
        'total': len(contracts),
        'paid': sum(1 for c in contracts if c.get('status_payment') == 'paid'),
        'unpaid': sum(1 for c in contracts if c.get('status_payment') == 'unpaid'),
        'approved': sum(1 for c in contracts if c.get('status') == 'approved'),
    }
    active_periods = [p for p in periods if 'endtime' in p and datetime.strptime(p['endtime'].split('T')[0], '%Y-%m-%d').date() >= datetime.now().date()]

    # 3. TẠO NỘI DUNG BÁO CÁO TXT (TỐI ƯU CHUNKING)
    report_content = []

    # --- PHẦN I: THÔNG TIN TỔNG QUAN HỆ THỐNG ---
    report_content.append("I. THÔNG TIN TỔNG QUAN HỆ THỐNG")
    report_content.append(f"Tổng số khu KTX đang quản lý: {len(areas)}")
    report_content.append(f"Danh sách khu KTX: {', '.join([area.get('name', 'N/A') for area in areas])}")
    for area in areas:
        report_content.append(f" - KTX {area.get('name', 'N/A')}")
        report_content.append(f"   Địa chỉ: {area.get('address', 'N/A')}")
        report_content.append(f"   Cơ sở: {area.get('branch', 'N/A')}")
        report_content.append(f"   Mô tả: {area.get('description', 'N/A')}")
        report_content.append(f"   Phí/giá ở/giá thuê/giá hàng tháng/tiền phòng: {area.get('fee', 'N/A')} VND / tháng")
        report_content.append(f"   Trạng thái: {"Đang hoạt động" if area.get('status', 'N/A') == 'active' else "Ngừng hoạt động"}")
    report_content.append(f"Số đợt đăng ký đang/sắp diễn ra: {len(active_periods)}\n\n")
    report_content.append(f"Gồm các đợt đăng ký: {', '.join([p.get('name', 'N/A') for p in active_periods])}")
    report_content.append("\n")

    # --- PHẦN II: DANH SÁCH CÁN BỘ QUẢN TÚC ---
    report_content.append("II. DANH SÁCH CÁN BỘ QUẢN TÚC")
    if managers:
        for manager in managers:
            name = manager.get('fullname', 'N/A')
            report_content.append(f"Cán bộ: {name} | Địa điểm: KTX {manager.get('area_id', 'N/A')}")
        report_content.append(f"Tổng số cán bộ quản túc: {len(managers)}")
    else:
        report_content.append("Hiện không có danh sách cán bộ quản túc.")
    report_content.append("\n")

    # --- PHẦN III: TÌNH TRẠNG ĐƠN NGUYỆN VỌNG ---
    report_content.append("III. TÌNH TRẠNG ĐƠN NGUYỆN VỌNG")
    report_content.append(f"Tổng số đơn nguyện vọng đã nhận: {app_stats['total']}")
    report_content.append(f"Số đơn đang chờ duyệt: {app_stats['pending']}")
    report_content.append(f"Số đơn đã được duyệt: {app_stats['approved']}")
    report_content.append(f"Số đơn đã bị hủy/từ chối: {app_stats['rejected']}\n\n)")

    # --- PHẦN IV: TÌNH TRẠNG HỢP ĐỒNG & THANH TOÁN ---
    report_content.append("IV. TÌNH TRẠNG HỢP ĐỒNG & THANH TOÁN")
    report_content.append(f"Tổng số hợp đồng đã tạo: {contract_stats['total']}")
    report_content.append(f"Số hợp đồng đã được duyệt chính thức: {contract_stats['approved']}")
    report_content.append(f"Số hợp đồng đã thanh toán: {contract_stats['paid']}")
    report_content.append(f"Số hợp đồng chưa thanh toán: {contract_stats['unpaid']}\n\n")

    # --- PHẦN V: CHI TIẾT CÁC ĐỢT ĐĂNG KÝ ---
    report_content.append("V. CHI TIẾT CÁC ĐỢT ĐĂNG KÝ")
    if periods:
        for p in periods:
            try:
                name = p.get('name', 'N/A')
                start_date = datetime.strptime(p['starttime'].split('T')[0], '%Y-%m-%d').strftime('%d/%m/%Y') if 'starttime' in p and p['starttime'] else 'N/A'
                end_date = datetime.strptime(p['endtime'].split('T')[0], '%Y-%m-%d').strftime('%d/%m/%Y') if 'endtime' in p and p['endtime'] else 'N/A'
                status = p.get('status', 'N/A')
                description = p.get('description', 'N/A')

                report_content.append(f"Đợt: {name} | Thời gian: {start_date} - {end_date} | Trạng thái: {status} | Mô tả: {description}")
            except Exception as e:
                report_content.append(f"Lỗi xử lý thông tin đợt đăng ký: {str(e)}")
        report_content.append("\n")
    else:
        report_content.append("Hiện không có đợt đăng ký nào.")
        report_content.append("\n")

    # --- PHẦN VI: LỊCH TRỰC CÁN BỘ QUẢN TÚC ---
    report_content.append("VI. LỊCH TRỰC CÁN BỘ QUẢN TÚC")
    if duty_schedules:
        for schedule in duty_schedules:
            date_str = schedule.get('date', 'N/A')
            area_id = schedule.get('area_id', 'N/A')
            staff = schedule.get('staff', {})
            staff_name = staff.get('fullname', 'N/A')
            report_content.append(f"Ngày: {date_str} | Khu KTX: {area_id} | Cán bộ: {staff_name}")
    else:
        report_content.append("Hiện không có lịch trực nào được lên kế hoạch.")
    report_content.append("-" * 50)

    # 4. LƯU VÀO FILE
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        final_content = '\n'.join(report_content)
        # Sử dụng replace để đảm bảo ngắt đoạn mạnh mẽ hơn cho việc chia chunk (\n\n)
        f.write(final_content.replace('\n\n\n', '\n\n'))

    print("\n✅ BÁO CÁO ĐÃ ĐƯỢC TẠO THÀNH CÔNG!")
    print(f"File báo cáo nằm tại: {os.path.abspath(REPORT_FILE)}")
    return True  # Trả về True nếu báo cáo được tạo thành công


def load_text_file_robustly(file_path):
    """
    Hàm riêng để tải file .txt một cách mạnh mẽ, thử nhiều mã hóa khác nhau
    """
    try:
        # 1. Thử tải bằng tự động dò mã hóa (autodetect)
        loader = TextLoader(file_path, autodetect_encoding=True)
        return loader.load()
    except Exception:
        # 2. Nếu thất bại, thử buộc mã hóa UTF-8
        try:
            loader = TextLoader(file_path, encoding='utf-8')
            return loader.load()
        except Exception as e_utf8:
            raise Exception(f"Không thể tải file TXT ngay cả với UTF-8. ỗi gốc: {e_utf8}")


def setup_database():
    """
    Thực hiện 4 bước:
    1. Tự động tạo báo cáo KTX (thông tin mới nhất).
    2. Tải tài liệu TXT với xử lý lỗi.
    3. Chia nhỏ thành chunks.
    4. Tạo embeddings và lưu vào ChromaDB.
    """

    # 1. TỰ ĐỘNG TẠO BÁO CÁO MỚI NHẤT
    token = get_access_token()
    if token:
        generate_report(token)
    else:
        print("\n[Bỏ qua bước tạo báo cáo tự động]: Đăng nhập không thành công hoặc không có token.")
    print("\n--- BƯỚC 1: XỬ LÝ DỮ LIỆU ĐẦU VÀ TẠO DATABASE ---")
    documents = []
    if not os.path.exists(DATA_FOLDER):
        print("❌ Lỗi: Thư mục '{DATA_FOLDER}' không tồn tại.")
        return None

    # 2. Tải tài liệu từ thư mục và xử lý lỗi
    print("Xử lý file txt")
    txt_file_paths = glob.glob(os.path.join(DATA_FOLDER, "**/*.txt"), recursive=True)
    if not txt_file_paths:
        print("Lỗi: Không tìm thấy bất kỳ file txt nào trong thư mục")
        return None
    for file_path in txt_file_paths:
        try:
            documents.extend(load_text_file_robustly(file_path))
        except Exception as e:
            # print(f"❌ CANH BAO: Khong the tai file '{file_path}'. Loi: {e}")
            print(f"❌ CANH BAO: Không thể tải file '{file_path}' do lỗi: {e}")
    if not documents:
        print("Lỗi: Không tìm thấy tài liệu nào trong thư mục. Vui lòng thêm file vào.")
        return None

    print(f"✅ Đã tải thành công {len(documents)} tài liệu.")

    # 3. Chia nhỏ tài liệu thành chunks
    print(f"-> Dang chia nho tai lieu thanh chunks (Kich thuoc: {CHUNK_SIZE}, Chong lan: {CHUNK_OVERLAP})...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"✅ Da chia nho thanh {len(chunks)} doan (chunks).")

    # 4. Tạo Embeddings và lưu vào ChromaDB
    print(f"-> Dang khoi tao mo hinh nhung: {EMBEDDING_MODEL_NAME}...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    """
    Kiểm tra nếu db đã tồn tại thì xóa dữ liệu cũ trước khi thêm mới
    Nếu không thì tạo mới
    """
    if os.path.exists(VECTOR_DB_PATH):
        vectorstore = Chroma(
            persist_directory=VECTOR_DB_PATH,
            embedding_function=embeddings
        )
        vectorstore.delete(ids=vectorstore.get()['ids'])
        print("-> Đã xóa dữ liệu cũ trong collection, đang thêm dữ liệu mới...")
        vectorstore.add_documents(documents=chunks)
    else:
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=VECTOR_DB_PATH
        )
        print("-> Đã tạo collection mới")

    return vectorstore
