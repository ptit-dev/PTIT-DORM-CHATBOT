import os
from dotenv import load_dotenv
from .validators import validate_system_prompt

load_dotenv()


class Config:
    def __init__(self):
        self.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        self.backend_api_url = os.getenv('BACKEND_API_URL', '')
        self.backend_api_key = os.getenv('BACKEND_API_KEY', '')
        self.llm_model_name = os.getenv('LLM_MODEL_NAME', 'gemma-3-27b-it')
        self.temperature = float(os.getenv('TEMPERATURE', '0.2'))
        self.max_context_tokens = int(os.getenv('MAX_CONTEXT_TOKENS', '4000'))
        self.max_response_tokens = int(os.getenv('MAX_RESPONSE_TOKENS', '2000'))
        self.vector_db_path = os.getenv('VECTOR_DB_PATH', 'rag_chroma_db')
        self.embedding_model_name = os.getenv('EMBEDDING_MODEL_NAME', 'bkai-foundation-models/vietnamese-bi-encoder')
        self.chunk_size = int(os.getenv('DB_CHUNK_SIZE', '1000'))
        self.chunk_overlap = int(os.getenv('DB_CHUNK_OVERLAP', '100'))
        self.retrieval_k_chunks = int(os.getenv('RAG_RETRIEVAL_K_CHUNKS', '5'))
        self.max_messages = int(os.getenv('RATE_LIMIT_MAX_MESSAGES', '1'))
        self.time_window_seconds = int(os.getenv('RATE_LIMIT_TIME_WINDOW_SECONDS', '10'))
        self.max_connections = int(os.getenv('MAX_CONNECTIONS', '100'))
        self.idle_timeout_seconds = int(os.getenv('IDLE_TIMEOUT_SECONDS', '30'))
        self.admin_api_key = os.getenv('ADMIN_API_KEY')
        self.status_interval_seconds = int(os.getenv('STATUS_INTERVAL_SECONDS', '60'))
        self.reload_interval_seconds = int(os.getenv('RELOAD_INTERVAL_SECONDS', '200000'))
        self.system_prompt = (
            "Bạn là **Chatbot Hỗ trợ Thông tin Ký túc xá PTIT**. Nhiệm vụ của bạn là cung cấp câu trả lời **trực tiếp, ngắn gọn và hữu ích** cho sinh viên.\n\n"
            "QUY TẮC BẮT BUỘC:\n"
            "1. **Chỉ trả lời** dựa trên thông tin có trong phần 'NGỮ CẢNH'. KHÔNG tự suy luận, bịa đặt hay thêm thông tin ngoài ngữ cảnh.\n"
            "2. **Giọng điệu:** Thân thiện, dễ thương, đầy đủ xưng hô, chuyên nghiệp và rõ ràng.\n"
            "3. **Cấu trúc trả lời:** Đi thẳng vào câu hỏi, tránh dùng các cụm từ mở đầu như 'Theo ngữ cảnh...', 'Dưới đây là thông tin tôi tìm thấy...'.\n"
            "4. **Xử lý thiếu thông tin:** Nếu 'NGỮ CẢNH' KHÔNG CÓ thông tin để trả lời, Trả lời theo ý: 'Xin lỗi, Mình đã kiểm tra nhưng chưa thấy thông tin về nội dung này. Bạn vui lòng liên hệ Ban Quản lý KTX để được hỗ trợ thêm nhé.'\n"
            "5. Trả lời đầy đủ thông tin có trong ngữ cảnh, không được tự ý tóm tắt hoặc cắt ngắn nội dung.\n\n"
        )

        @property
        def system_prompt(self):
            return self._system_prompt
        
        @system_prompt.setter
        def system_prompt(self, value):
            try:
                validate_system_prompt(value)
                self._system_prompt = value
            except ValueError as e:
                raise ValueError(f"Invalid system prompt: {str(e)}")