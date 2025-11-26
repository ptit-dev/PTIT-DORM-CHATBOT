import os
import sys
import shutil
import traceback 
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from typing import Optional, Tuple
from langchain_core.language_models.llms import LLM 
from google.genai.errors import APIError as GoogleAPIError

# Chữa lỗi Unicode trên Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# CẤU HÌNH API
load_dotenv()
os.environ['GOOGLE_API_KEY'] = os.getenv('GOOGLE_API_KEY') 
VECTOR_DB_PATH = "rag_chroma_db"

# LLM_MODEL_ID = "gemini-2.5-flash" 
LLM_MODEL_ID = "gemini-2.5-flash-lite"

# EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-large" 
# EMBEDDING_MODEL_NAME = "vinai/phobert-base"
EMBEDDING_MODEL_NAME = "bkai-foundation-models/vietnamese-bi-encoder"

API_TIMEOUT_SECONDS = 60
RETRIEVAL_K_CHUNKS = 5

def load_llm_and_db() -> Tuple[Optional[LLM], Optional[Chroma]]:
    """
    Tải LLM (Cloud API) và Vector Database đã tạo.
    """
    print("--- 1. KHỞI TẠO MÔ HÌNH LLM (GOOGLE GEMINI API) ---")
    try:
        if not os.getenv('GOOGLE_API_KEY'):
            print("🔴 LỖI: GOOGLE_API_KEY chưa được thiết lập trong file .env")
            return None, None
        
        llm = GoogleGenerativeAI(
            model=LLM_MODEL_ID,  
            temperature=0.2, 
            max_output_tokens=3069,
        )

        print(f"✅ Khởi tạo LLM {LLM_MODEL_ID} (Gemini API) thành công. Timeout: {API_TIMEOUT_SECONDS}s")
    except GoogleAPIError as e:
        print(f"🔴 LỖI KHỞI TẠO LLM (API ERROR): {e}")
        print("Vui lòng kiểm tra tình trạng GOOGLE_API_KEY (đã hết hạn hoặc bị chặn).")
        return None, None
    except Exception as e:
        print(f"🔴 LỖI KHỞI TẠO LLM: {e}")
        return None, None

    print("\n--- 2. TẢI VECTOR DATABASE ---")
    if not os.path.exists(VECTOR_DB_PATH):
        print(f"🔴 LỖI: Thư mục database '{VECTOR_DB_PATH}' không tồn tại. Vui lòng chạy ingestion.")
        return llm, None

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    vectorstore = Chroma(
        persist_directory=VECTOR_DB_PATH,
        embedding_function=embeddings
    )
    print("✅ Tải Vector Database thành công.")

    return llm, vectorstore

def generate_response(llm: LLM, vectorstore: Chroma, question: str):
    """
    Thực hiện luồng RAG: Retrieval (Truy vấn) -> Augmentation (Tăng cường) -> Generation (Tạo câu trả lời).
    """
    print(f"\n--- 3. THỰC HIỆN TRUY VẤN RAG cho câu hỏi: {question} ---")
    
    # Retrieval: LẤY RETRIEVAL_K_CHUNKS (5 chunks)
    retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVAL_K_CHUNKS}) 
    retrieved_docs = retriever.invoke(question)
    
    # Augmentation: Hợp nhất ngữ cảnh (loại bỏ xuống dòng thừa)
    context_text = "\n".join([" ".join(doc.page_content.split()) for doc in retrieved_docs])

    template = (
        "Bạn là **Chatbot Hỗ trợ Thông tin Ký túc xá PTIT**. Nhiệm vụ của bạn là cung cấp câu trả lời **trực tiếp, ngắn gọn và hữu ích** cho sinh viên.\n\n"

        "QUY TẮC BẮT BUỘC:\n"
        "1. **Chỉ trả lời** dựa trên thông tin có trong phần 'NGỮ CẢNH'. KHÔNG tự suy luận, bịa đặt hay thêm thông tin ngoài ngữ cảnh.\n"
        "2. **Giọng điệu:** Thân thiện, dễ thương, đầy đủ xưng hô, chuyên nghiệp và rõ ràng.\n"
        "3. **Cấu trúc trả lời:** Đi thẳng vào câu hỏi, tránh dùng các cụm từ mở đầu như 'Theo ngữ cảnh...', 'Dưới đây là thông tin tôi tìm thấy...'.\n"
        "4. **Xử lý thiếu thông tin:** Nếu 'NGỮ CẢNH' KHÔNG CÓ thông tin để trả lời, Trả lời đại ý kiểu: 'Xin lỗi, Mình đã kiểm tra nhưng chưa thấy thông tin về nội dung này. Bạn vui lòng liên hệ Ban Quản lý KTX để được hỗ trợ thêm nhé.'"
        "5. Trả lời thật đầy đủ thông tin \n\n"

        "NGỮ CẢNH:\n"
        "--- Bối cảnh dữ liệu hiện tại (Ngày {current_date}) ---\n"
        "{context}\n"
        "--- KẾT THÚC NGỮ CẢNH ---\n\n"

        "Câu hỏi của sinh viên:\n"
        "{question}\n\n"

        "Hãy đưa ra câu trả lời **trực tiếp**:"
    )
    
    rag_prompt = PromptTemplate(
        template=template,
        input_variables=["context", "question", "current_date"]
    )

    from datetime import datetime
    current_date = datetime.now().strftime("%d/%m/%Y")
    final_prompt = rag_prompt.format(context=context_text, question=question, current_date=current_date)

    print(f"-> Prompt (đầu vào LLM):\n{final_prompt}")
    print(f"-> BẮT ĐẦU gọi API đến LLM ({LLM_MODEL_ID}) qua Cloud API...")
    
    try:
        response = llm.invoke(final_prompt)
        print("-> KẾT THÚC gọi API thành công.")
        
        # KIỂM TRA ĐẦU RA RỖNG (EMPTY STRING CHECK)
        if not response or response.strip() == "":
            return "Xin lỗi, mô hình LLM đã không thể tạo ra câu trả lời hợp lệ dựa trên ngữ cảnh được cung cấp. Vui lòng thử lại hoặc thay đổi câu hỏi."
            
        return response
    except Exception as e:
        # Xử lý lỗi API (nếu có)
        traceback.print_exc()
        raise Exception(f"Lỗi khi gọi API Gemini: {str(e)}")

