from fastapi import FastAPI, WebSocket

from services.rag_service import RAGService
from services.database_service import DatabaseService
from middleware.rate_limiter import RateLimiter
from middleware.connection_manager import ConnectionManager
from middleware.cors_config import setup_cors
from middleware.chat_handler import ChatHandler
from middleware.app_lifecycle import AppLifecycle
from routers import AdminRouter

app = FastAPI(title="RAG Chatbot API", version="1.0.0")
setup_cors(app)

rag_service = RAGService()
db_service = DatabaseService()
rate_limiter = RateLimiter(max_messages=1, time_window_seconds=10)
connection_manager = ConnectionManager(max_connections=100, idle_timeout_seconds=30)

chat_handler = ChatHandler(rag_service, rate_limiter, connection_manager)
lifecycle = AppLifecycle(rag_service, db_service, connection_manager)

admin_router = AdminRouter(lifecycle, rag_service)
app.include_router(admin_router.router)


@app.on_event("startup")
async def startup():
    await lifecycle.startup()


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await chat_handler.handle_connection(websocket)
