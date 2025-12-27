import sys
import os
import glob
import requests
from datetime import datetime
from typing import Optional, List, Any

from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


class DatabaseService:
    
    VECTOR_DB_PATH = "rag_chroma_db"
    DATA_FOLDER = "data_documents"
    EMBEDDING_MODEL_NAME = "bkai-foundation-models/vietnamese-bi-encoder"
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 100
    REPORT_FILE = "data_documents/ThongKeKTX.txt"
    
    def __init__(self):
        load_dotenv()
        self.api_base_url = os.getenv("API_BASE_URL")
        self.admin_username = os.getenv("ADMIN_USERNAME_ENV")
        self.admin_password = os.getenv("ADMIN_PASSWORD_ENV")
    
    def get_access_token(self) -> Optional[str]:
        print("DB: Getting access token")
        login_url = f"{self.api_base_url}/login"
        try:
            response = requests.post(
                login_url,
                headers={"Content-Type": "application/json"},
                json={"username": self.admin_username, "password": self.admin_password}
            )
            response.raise_for_status()

            data = response.json()
            access_token = data.get('access_token')

            if access_token:
                print("DB: Token obtained")
                return access_token
            else:
                print("DB: No access_token in response")
                return None

        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if e.response is not None else 'Unknown'
            print(f"DB: Login error - Status {status_code}")
            return None

    def fetch_data(self, token: str, endpoint: str, params: dict = None) -> List[Any]:
        url = f"{self.api_base_url}{endpoint}"
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
            print(f"DB: API error {endpoint} - {e}")
            return []

    def generate_report(self, token: str) -> bool:
        if token is None:
            print("DB: Cannot generate report, no token")
            return False

        print("DB: Generating report")
        
        areas = self.fetch_data(token, "/api/v1/protected/dorm-areas")
        managers = self.fetch_data(token, "/api/v1/protected/managers")
        periods = self.fetch_data(token, "/api/v1/protected/registration-periods")
        applications = self.fetch_data(token, "/api/v1/protected/dorm-applications")
        contracts = self.fetch_data(token, "/api/v1/protected/contracts")
        duty_schedules = self.fetch_data(token, "/api/v1/protected/duty-schedules")

        areas = areas if isinstance(areas, list) else []
        managers = managers if isinstance(managers, list) else []
        periods = periods if isinstance(periods, list) else []
        applications = applications if isinstance(applications, list) else []
        contracts = contracts if isinstance(contracts, list) else []
        duty_schedules = duty_schedules if isinstance(duty_schedules, list) else []

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

        report_content = []

        report_content.append("I. THÔNG TIN TỔNG QUAN HỆ THỐNG")
        report_content.append(f"Tổng số khu KTX đang quản lý: {len(areas)}")
        report_content.append(f"Danh sách khu KTX: {', '.join([area.get('name', 'N/A') for area in areas])}")
        for area in areas:
            report_content.append(f" - KTX {area.get('name', 'N/A')}")
            report_content.append(f"   Địa chỉ: {area.get('address', 'N/A')}")
            report_content.append(f"   Cơ sở: {area.get('branch', 'N/A')}")
            report_content.append(f"   Mô tả: {area.get('description', 'N/A')}")
            report_content.append(f"   Phí/giá ở/giá thuê/giá hàng tháng/tiền phòng: {area.get('fee', 'N/A')} VND / tháng")
            report_content.append(f"   Trạng thái: {'Đang hoạt động' if area.get('status', 'N/A') == 'active' else 'Ngừng hoạt động'}")
        report_content.append(f"Số đợt đăng ký đang/sắp diễn ra: {len(active_periods)}\n\n")
        report_content.append(f"Gồm các đợt đăng ký: {', '.join([p.get('name', 'N/A') for p in active_periods])}")
        report_content.append("\n")

        report_content.append("II. DANH SÁCH CÁN BỘ QUẢN TÚC")
        if managers:
            for manager in managers:
                name = manager.get('fullname', 'N/A')
                report_content.append(f"Cán bộ: {name} | Địa điểm: KTX {manager.get('area_id', 'N/A')}")
            report_content.append(f"Tổng số cán bộ quản túc: {len(managers)}")
        else:
            report_content.append("Hiện không có danh sách cán bộ quản túc.")
        report_content.append("\n")

        report_content.append("III. TÌNH TRẠNG ĐƠN NGUYỆN VỌNG")
        report_content.append(f"Tổng số đơn nguyện vọng đã nhận: {app_stats['total']}")
        report_content.append(f"Số đơn đang chờ duyệt: {app_stats['pending']}")
        report_content.append(f"Số đơn đã được duyệt: {app_stats['approved']}")
        report_content.append(f"Số đơn đã bị hủy/từ chối: {app_stats['rejected']}\n\n)")

        report_content.append("IV. TÌNH TRẠNG HỢP ĐỒNG & THANH TOÁN")
        report_content.append(f"Tổng số hợp đồng đã tạo: {contract_stats['total']}")
        report_content.append(f"Số hợp đồng đã được duyệt chính thức: {contract_stats['approved']}")
        report_content.append(f"Số hợp đồng đã thanh toán: {contract_stats['paid']}")
        report_content.append(f"Số hợp đồng chưa thanh toán: {contract_stats['unpaid']}\n\n")

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

        os.makedirs(os.path.dirname(self.REPORT_FILE), exist_ok=True)
        with open(self.REPORT_FILE, 'w', encoding='utf-8') as f:
            final_content = '\n'.join(report_content)
            f.write(final_content.replace('\n\n\n', '\n\n'))

        print(f"DB: Report saved to {os.path.abspath(self.REPORT_FILE)}")
        return True

    def load_text_file_robustly(self, file_path: str):
        try:
            loader = TextLoader(file_path, autodetect_encoding=True)
            return loader.load()
        except Exception:
            try:
                loader = TextLoader(file_path, encoding='utf-8')
                return loader.load()
            except Exception as e_utf8:
                raise Exception(f"Không thể tải file TXT: {e_utf8}")

    def setup_database(self) -> Optional[Chroma]:
        token = self.get_access_token()
        if token:
            self.generate_report(token)
        else:
            print("DB: Skipping auto-report, no token")
        
        print("DB: Processing documents")
        documents = []
        
        if not os.path.exists(self.DATA_FOLDER):
            print(f"DB: Folder '{self.DATA_FOLDER}' not found")
            return None

        txt_file_paths = glob.glob(os.path.join(self.DATA_FOLDER, "**/*.txt"), recursive=True)
        if not txt_file_paths:
            print("DB: No txt files found")
            return None
        
        for file_path in txt_file_paths:
            try:
                documents.extend(self.load_text_file_robustly(file_path))
            except Exception as e:
                print(f"DB: Cannot load '{file_path}' - {e}")
        
        if not documents:
            print("DB: No documents loaded")
            return None

        print(f"DB: Loaded {len(documents)} documents")

        print(f"DB: Splitting chunks, size={self.CHUNK_SIZE}, overlap={self.CHUNK_OVERLAP}")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)
        print(f"DB: Created {len(chunks)} chunks")

        print(f"DB: Loading embedding model {self.EMBEDDING_MODEL_NAME}")
        embeddings = HuggingFaceEmbeddings(model_name=self.EMBEDDING_MODEL_NAME)
        
        if os.path.exists(self.VECTOR_DB_PATH):
            vectorstore = Chroma(
                persist_directory=self.VECTOR_DB_PATH,
                embedding_function=embeddings
            )
            vectorstore.delete(ids=vectorstore.get()['ids'])
            print("DB: Deleted old data, adding new")
            vectorstore.add_documents(documents=chunks)
        else:
            vectorstore = Chroma.from_documents(
                documents=chunks,
                embedding=embeddings,
                persist_directory=self.VECTOR_DB_PATH
            )
            print("DB: Created new collection")

        return vectorstore


db_service = DatabaseService()


def get_access_token():
    return db_service.get_access_token()


def fetch_data(token, endpoint, params=None):
    return db_service.fetch_data(token, endpoint, params)


def generate_report(token):
    return db_service.generate_report(token)


def load_text_file_robustly(file_path):
    return db_service.load_text_file_robustly(file_path)


def setup_database():
    return db_service.setup_database()
