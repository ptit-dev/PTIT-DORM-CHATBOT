# 🏢 PTIT Dorm Chatbot

Chatbot RAG (Retrieval-Augmented Generation) hỗ trợ tra cứu thông tin ký túc xá (KTX) Học viện Công nghệ Bưu chính Viễn thông (PTIT) sử dụng Google Gemini API và ChromaDB.

## ✨ Tính năng

- 🤖 **RAG Pipeline**: Kết hợp retrieval và generation để trả lời chính xác
- 🔄 **Auto-reload Database**: Tự động cập nhật database mỗi 30 giây
- 🌐 **WebSocket API**: Real-time chat với FastAPI
- 🛡️ **Rate Limiting**: Giới hạn 1 tin nhắn/15 giây mỗi client
- ⏱️ **Idle Timeout**: Tự động ngắt kết nối sau 30 giây không hoạt động
- 📊 **Connection Management**: Giới hạn tối đa 100 kết nối đồng thời
- 🇻🇳 **Vietnamese Optimized**: Embedding model tối ưu cho tiếng Việt

## 🏗️ Kiến trúc


## 📋 Yêu cầu hệ thống

- Python 3.8+
- Google API Key (Gemini)
- 4GB RAM trở lên (để load embedding model)

## 🚀 Cài đặt

### 1. Clone repository

```bash
git clone https://github.com/ptit-dev/PTIT-DORM-CHATBOT.git
cd PTIT-DORM-CHATBOT
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 3. Cấu hình environment variables

Tạo file `.env` trong thư mục gốc:

```env
GOOGLE_API_KEY=your_google_api_key_here
ADMIN_USERNAME_ENV=your_admin_username
ADMIN_PASSWORD_ENV=your_admin_password
API_BASE_URL=***
```

### 4. Chuẩn bị dữ liệu

Đặt các file văn bản (.txt) chứa thông tin KTX vào thư mục `data_documents/`:

```bash
mkdir data_documents
# Thêm các tài liệu cần thiết (định dạng txt)
```

### 5. Tạo Vector Database

```bash
python data_ingestion.py
```

### 6. Khởi động API Server

```bash
uvicorn api_service:app
```

Server sẽ chạy tại: `http://127.0.0.1:8000`

## 🔧 Cấu hình

### API Service (`api_service.py`)

```python
# Rate limiting
MAX_MESSAGES = 1              # Số tin nhắn tối đa
TIME_WINDOW_SECONDS = 15      # Trong khoảng thời gian (giây)

# Connection limits
MAX_CONNECTIONS = 100         # Số kết nối tối đa đồng thời

# Idle timeout
IDLE_TIMEOUT_SECONDS = 30     # Thời gian timeout (giây)

# Auto-reload interval
await asyncio.sleep(3 * 24 * 60 * 60)       # Reload mỗi 3 ngày
```

### Data Ingestion (`data_ingestion.py`)

```python
VECTOR_DB_PATH = "rag_chroma_db"                           # Đường dẫn database
EMBEDDING_MODEL_NAME = "bkai-foundation-models/vietnamese-bi-encoder"  # Model embedding
CHUNK_SIZE = 1000                                          # Kích thước chunk
CHUNK_OVERLAP = 100                                      
```

### RAG Logic (`rag_logic.py`)

```python
MODEL_NAME = "gemini-2.5-flash"  # Google Gemini model
TEMPERATURE = 0.1                     # Độ sáng tạo (0-1)
MAX_TOKENS = 2048                     # Số token tối đa
```

## 📡 API Endpoints

### WebSocket Chat

**Endpoint**: `ws://127.0.0.1:8000/ws/chat`

**Request**:
```json
"Câu hỏi của bạn về KTX"
```

**Response**:
```json
{
  "question": "Câu hỏi của bạn về KTX",
  "answer": "Câu trả lời từ chatbot",
  "status": "success"
}
```

**Status codes**:
- `success`: Trả lời thành công
- `rate_limited`: Vượt quá rate limit
- `timeout`: Kết nối timeout
- `error`: Lỗi server

## 🧪 Test thử

### Python Client

```python
import asyncio
import websockets
import json

async def test_chatbot():
    uri = "ws://127.0.0.1:8000/ws/chat"
    async with websockets.connect(uri) as websocket:
        # Gửi câu hỏi
        await websocket.send("Thông tin về KTX PTIT")
        
        # Nhận câu trả lời
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Câu trả lời: {data['answer']}")

asyncio.run(test_chatbot())
```

### JavaScript Client

```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/ws/chat');

ws.onopen = () => {
  ws.send('Thông tin về KTX PTIT');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Câu trả lời:', data.answer);
};
```

## 📁 Cấu trúc thư mục

```
PTIT-DORM-CHATBOT/
├── api_service.py          # FastAPI WebSocket server
├── rag_logic.py            # RAG pipeline logic
├── data_ingestion.py       # Xử lý và tạo vector database
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (không commit)
├── .gitignore             # Git ignore rules
├── README.md              # Tài liệu này
├── data_documents/        # Thư mục chứa dữ liệu gốc (.txt)
└── rag_chroma_db/         # Vector database (ChromaDB)
```

## 🔐 Bảo mật

- ✅ CORS được cấu hình cho phép all origins (production nên hạn chế)
- ✅ Rate limiting ngăn chặn spam
- ✅ Connection limits ngăn chặn DoS
- ✅ Idle timeout giải phóng tài nguyên
- ⚠️ `.env` file không được commit lên git

## 🐛 Troubleshooting

### Lỗi: "No module named 'langchain'"

```bash
pip install langchain langchain-google-genai
```

### Lỗi: "GOOGLE_API_KEY not found"

Kiểm tra file `.env` và đảm bảo đã cấu hình đúng API key.

### Lỗi: "Unable to load embedding model"

Model sẽ tự động tải về lần đầu chạy. Đảm bảo có kết nối internet ổn định.

### Database không tự động reload

Kiểm tra terminal logs để xem có lỗi trong quá trình reload không.

## 📝 TODO

- [ ] Thêm authentication cho WebSocket
- [ ] Health check endpoint
- [ ] Metrics và monitoring
- [ ] Docker containerization
- [ ] CI/CD pipeline


## 📄 License

Dự án này thuộc về ptit-dev

⭐ Nếu project hữu ích, đừng quên star repo nhé!