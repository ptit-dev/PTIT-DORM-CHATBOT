import os
from dotenv import load_dotenv

load_dotenv()


class ConfigService:
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.llm_model_name = os.getenv("LLM_MODEL_NAME", "gemma-3-27b-it")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.23"))
        
        self.reload_interval = int(os.getenv("RELOAD_INTERVAL_SECONDS", str(3 * 24 * 60 * 60)))
        self.status_interval = int(os.getenv("STATUS_INTERVAL_SECONDS", str(60 * 10)))
        
        self.system_prompt = (
            "Bạn là **Chatbot Hỗ trợ Thông tin Ký túc xá PTIT**. Nhiệm vụ của bạn là cung cấp câu trả lời **trực tiếp, ngắn gọn và hữu ích** cho sinh viên.\n\n"
            "QUY TẮc BẮT BUỘC:\n"
            "1. **Chỉ trả lời** dựa trên thông tin có trong phần 'NGỮ CẢNH'. KHÔNG tự suy luận, bịa đặt hay thêm thông tin ngoài ngữ cảnh.\n"
            "2. **Giọng điệu:** Thân thiện, dễ thương, đầy đủ xưng hô, chuyên nghiệp và rõ ràng.\n"
            "3. **Cấu trúc trả lời:** Đi thẳng vào câu hỏi, tránh dùng các cụm từ mở đầu như 'Theo ngữ cảnh...', 'Dưới đây là thông tin tôi tìm thấy...'.\n"
            "4. **Xử lý thiếu thông tin:** Nếu 'NGỮ CẢNH' KHÔNG CÓ thông tin để trả lời, Trả lời theo ý: 'Xin lỗi, Mình đã kiểm tra nhưng chưa thấy thông tin về nội dung này. Bạn vui lòng liên hệ Ban Quản lý KTX để được hỗ trợ thêm nhé.'"
            "5. Trả lời đầy đủ thông tin có trong ngữ cảnh, không được tự ý tóm tắt hoặc cắt ngắn nội dung.\n\n"
        )


config_service = ConfigService()
