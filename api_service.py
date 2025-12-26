import sys
import time
import asyncio
from fastapi import FastAPI
from fastapi import WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_logic import load_llm_and_db, generate_response
from data_ingestion import setup_database
import uvicorn

# Quản lý rate limit
RATE_LIMIT_STORE = {}
MAX_MESSAGES = 1
TIME_WINDOW_SECONDS = 10
RATE_LIMIT_LOCK = asyncio.Lock()

# Quản lý connection limit
MAX_CONNECTIONS = 100
active_connections_count = 0
CONNECTION_COUNT_LOCK = asyncio.Lock()

# Quản lý idle timeout
IDLE_TIMEOUT_SECONDS = 30
LAST_ACTIVITY = {}

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

app = FastAPI(title="RAG Chatbot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llama_llm = None
vectorstore = None


class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    question: str
    answer: str
    status: str


# Quản lý Reload Database
IS_RELOADING_DB = False
RELOAD_DB_LOCK = asyncio.Lock()
RELOAD_DB_INTERVAL = 3 * 24 * 60 * 60


async def auto_reload_database():
    """Hàm tự động reload database mỗi 3 ngày"""
    global vectorstore, IS_RELOADING_DB, llama_llm

    while True:
        async with RELOAD_DB_LOCK:
            if IS_RELOADING_DB:
                print("⏭️  Database đang được reload, bỏ qua chu kỳ này")
                continue
            IS_RELOADING_DB = True

        try:
            print("\n🔄 BẮT ĐẦU RELOAD DATABASE (Chu kỳ 3 ngày)...")

            # 1. Chạy setup_database để tạo database mới
            print("1. Tạo database mới với setup_database()...")
            await asyncio.to_thread(setup_database)
            print("✅ Database mới đã được tạo thành công")

            # 2. Reload LLM và DB
            print("2. Đang load lại LLM và Database...")
            llama_llm, vectorstore = load_llm_and_db()
            print("✅ LLM và Database đã được load lại")

            # 3. Xác nhận hoàn thành
            if llama_llm and vectorstore:
                print("✅ RELOAD DATABASE THÀNH CÔNG!\n")
            else:
                print("⚠️  Cảnh báo: LLM hoặc Database có thể chưa sẵn sàng\n")

        except Exception as e:
            print(f"❌ LỖI RELOAD DATABASE: {str(e)}\n")

        finally:
            async with RELOAD_DB_LOCK:
                IS_RELOADING_DB = False

        await asyncio.sleep(RELOAD_DB_INTERVAL)  # Reload mỗi 3 ngày


async def server_status_reporter():
    """log thông tin server mỗi 10 phút"""
    while True:
        await asyncio.sleep(60*10)
        print("\n" + "="*60)
        print(f"📊 THÔNG TIN SERVER (Kết nối: {active_connections_count}/{MAX_CONNECTIONS})")
        print(f"   • Rate Limit Store: {len(RATE_LIMIT_STORE)} clients")
        print(f"   • Last Activity: {len(LAST_ACTIVITY)} clients")
        print("="*60 + "\n")


@app.on_event("startup")
async def startup_event():
    global llama_llm, vectorstore
    print("🚀 Khởi động API Service...")
    llama_llm, vectorstore = load_llm_and_db()

    if llama_llm and vectorstore:
        print("✅ LLM và Vector Database đã sẵn sàng!")
    else:
        print("🔴 Lỗi: Không thể tải LLM hoặc Database")

    asyncio.create_task(server_status_reporter())
    asyncio.create_task(auto_reload_database())


async def check_rate_limit(websocket: WebSocket) -> bool:
    """Kiểm tra và áp dụng rate limit cho mỗi client."""
    client_id = id(websocket)
    current_time = time.time()

    async with RATE_LIMIT_LOCK:
        timestamps = [t for t in RATE_LIMIT_STORE.get(client_id, []) if t > current_time - TIME_WINDOW_SECONDS]

        if len(timestamps) >= MAX_MESSAGES:
            time_to_wait = (timestamps[0] + TIME_WINDOW_SECONDS) - current_time
            print(f"Client {client_id} vượt quá rate limit. Đợi {time_to_wait:.2f}s")

            try:
                await websocket.send_json({
                    "answer": "Bạn gửi quá nhanh. Vui lòng chờ một chút trước khi gửi lại.",
                    "status": "rate_limited"
                })
            except Exception:
                pass
            return False

        timestamps.append(current_time)
        RATE_LIMIT_STORE[client_id] = timestamps
        return True


async def check_idle_timeout(websocket: WebSocket, client_id: int):
    """Theo dõi hoạt động và ngắt kết nối nếu không có tin nhắn trong thời gian quy định."""
    while True:
        await asyncio.sleep(10)

        if websocket.client_state != status.WS_CONNECTED:
            break

        last_activity_time = LAST_ACTIVITY.get(client_id, time.time())
        current_time = time.time()

        if (current_time - last_activity_time) > IDLE_TIMEOUT_SECONDS:
            print(f"⌛ Kết nối {client_id} không hoạt động, tự động ngắt.")
            try:
                await websocket.send_json({"answer": f"Kết nối đã bị ngắt do không hoạt động trong {IDLE_TIMEOUT_SECONDS} giây.", "status": "timeout"})
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
            except Exception:
                pass
            break


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    global active_connections_count
    client_id = id(websocket)
    timeout_task = None

    async with CONNECTION_COUNT_LOCK:
        if active_connections_count >= MAX_CONNECTIONS:
            print("🔴 Kết nối bị từ chối: Đã đạt giới hạn kết nối tối đa.")
            try:
                await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER, reason="Server capacity reached")
            except Exception:
                pass
            return
        active_connections_count += 1

    await websocket.accept()
    print(f"✅ Kết nối mới chấp nhận: {client_id}. Tổng kết nối: {active_connections_count}")

    LAST_ACTIVITY[client_id] = time.time()
    timeout_task = asyncio.create_task(check_idle_timeout(websocket, client_id))

    if not llama_llm or not vectorstore:
        try:
            await websocket.send_json({"answer": "🔴 Lỗi: LLM hoặc Database chưa được tải. Vui lòng thử lại sau.", "status": "error"})
            await websocket.close(code=1011)
        except Exception:
            pass
    try:
        while True:
            data = await websocket.receive_text()
            LAST_ACTIVITY[client_id] = time.time()

            print(f"📝 Câu hỏi từ client {client_id}: {data}")

            if not data.strip():
                continue

            if not await check_rate_limit(websocket):
                continue

            answer = generate_response(llama_llm, vectorstore, data)
            await websocket.send_json({"question": data, "answer": answer.strip(), "status": "success"})
    except WebSocketDisconnect:
        print(f"❌ Client {client_id} đã ngắt kết nối.")
    except Exception as e:
        print(f"🔴 Lỗi khi xử lý WebSocket {client_id}: {str(e)}")
        try:
            await websocket.send_json({"answer": "🔴 Lỗi Server nội bộ khi xử lý RAG. Vui lòng thử lại.", "status": "error"})
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
    finally:
        if timeout_task:
            timeout_task.cancel()

        async with CONNECTION_COUNT_LOCK:
            active_connections_count -= 1
            print(
                f"Ngắt kết nối với {client_id}. "
                f"Tổng kết nối còn lại: {active_connections_count}"
            )

        LAST_ACTIVITY.pop(client_id, None)
        async with RATE_LIMIT_LOCK:
            RATE_LIMIT_STORE.pop(client_id, None)
