# 🏢 PTIT DORM CHATBOT (RAG)

Chatbot hỗ trợ tra cứu thông tin Ký túc xá (KTX) Học viện Công nghệ Bưu chính Viễn thông (PTIT), được xây dựng dựa trên kiến trúc RAG (Retrieval-Augmented Generation), sử dụng Google Gemini API và ChromaDB.

## 🚀 CÔNG NGHỆ CỐT LÕI
- 🇻🇳 **Sử dụng mô hình embedding chuyên biệt cho Tiếng Việt**: bkai-foundation-models/vietnamese-bi-encoder
- 🌐 **Real-time Chat**: WebSocket API (FastAPI)
- 🔄 **Quản lý tài nguyên**:
  - Tự động cập nhật Database theo lịch
  - Giới hạn Rate Limiting (1 tin/10s) và Connection Limit (tối đa 100 kết nối)
  - Idle Timeout (30s) tự động ngắt kết nối rảnh rỗi

## ⚙️ YÊU CẦU & CÀI ĐẶT

### 1. Yêu cầu hệ thống

- Python 3.10+
- Google API Key (Gemini)
- RAM 4GB trở lên (để tải embedding model)

### 2. Thiết lập dự án

```bash
# 1. Clone Repository
git clone https://github.com/ptit-dev/PTIT-DORM-CHATBOT.git
cd PTIT-DORM-CHATBOT

# 2. Cài đặt Dependencies
pip install -r requirements.txt

# 3. Chuẩn bị Dữ liệu
mkdir data_documents
# Đặt các file thông tin KTX (.txt) vào đây

# 4. Tạo file .env
Chứa các biến môi trường sau:
GOOGLE_API_KEY=your_google_api_key_here
ADMIN_USERNAME_ENV=your_admin_username
DMIN_PASSWORD_ENV=your_admin_password
API_BASE_URL=***
```

### 3. Khởi động

**Khởi động API Server:**
```bash
uvicorn api_service:app
```

Server sẽ chạy tại: `http://127.0.0.1:8000`

## 🛠️ CẤU HÌNH QUAN TRỌNG

Các tham số có thể chỉnh sửa trong các file `api_service.py`, `data_ingestion.py` và `rag_logic.py`.

### API (FastAPI)

| Tham số | Giá trị mặc định | Mô tả |
|---------|------------------|-------|
| `MAX_MESSAGES` | 1 | Số tin nhắn tối đa |
| `TIME_WINDOW_SECONDS` | 10 | Khoảng thời gian Rate Limit (giây) |
| `MAX_CONNECTIONS` | 100 | Kết nối đồng thời tối đa |
| `IDLE_TIMEOUT_SECONDS` | 30 | Thời gian timeout kết nối (giây) |
| Auto-reload Interval | 3 ngày | Tần suất cập nhật Database |

### RAG & Database

| Tham số | Giá trị mặc định | Mô tả |
|---------|------------------|-------|
| `VECTOR_DB_PATH` | `"rag_chroma_db"` | Thư mục database |
| `EMBEDDING_MODEL_NAME` | `"bkai-foundation-models/vietnamese-bi-encoder"` | Embedding model được fine-tune cho tiếng Việt |
| `CHUNK_SIZE` | 1000 | Kích thước văn bản (chunk) |
| `CHUNK_OVERLAP` | 100 | Độ chồng lấn giữa các chunk văn bản |
| `MODEL_NAME` | `"gemma-3-27b-it"` | LLM được sử dụng |
| `TEMPERATURE` | 0.23 | Độ sáng tạo của câu trả lời (0-1) |

## 📡 API ENDPOINT (WEBSOCKET CHAT)

**Endpoint:** `ws://127.0.0.1:8000/ws/chat`

| Mục | Request (Gửi đi) | Response (Nhận về) |
|-----|------------------|-------------------|
| **Định dạng** | Câu hỏi của bạn về KTX (string) | `{ "question": "...", "answer": "...", "status": "..." }` |
| **Status Codes** | N/A | `success`, `rate_limited`, `timeout`, `error` |

### Ví dụ Test (Python Client)

```python
import asyncio
import websockets
import json

async def test_chatbot():
    uri = "ws://127.0.0.1:8000/ws/chat"
    async with websockets.connect(uri) as websocket:
        await websocket.send("Thông tin về KTX PTIT") # Gửi câu hỏi
        response = await websocket.recv()           # Nhận câu trả lời
        data = json.loads(response)
        print(f"Câu trả lời: {data['answer']}")

asyncio.run(test_chatbot())
```

## 📁 CẤU TRÚC CƠ BẢN

```
PTIT-DORM-CHATBOT/
├── api_service.py      # Server (FastAPI WebSocket)
├── rag_logic.py        # Logic RAG (Gemini + Retrieval)
├── data_ingestion.py   # Xử lý dữ liệu & tạo Vector DB
├── requirements.txt
├── .env                # Biến môi trường
├── data_documents/     # Dữ liệu nguồn (.txt)
└── rag_chroma_db/      # Vector database (ChromaDB)
```

## 🛡️ BẢO MẬT & GHI CHÚ

- ✅ **Đã áp dụng**: CORS, Rate Limiting, Connection Limits, Idle Timeout
- ⚠️ **Lưu ý**: File `.env` chứa API Key không được commit lên Git
- 📝 **Cần làm thêm (TODO)**: Authentication cho WebSocket, Health check, Docker, CI/CD

## 📄 LICENSE

Dự án này thuộc về **ptit-dev**.

---

⭐ **Nếu project hữu ích, đừng quên star repo nhé!**
