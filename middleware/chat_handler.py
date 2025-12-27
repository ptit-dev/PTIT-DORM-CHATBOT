import asyncio
from fastapi import WebSocket, WebSocketDisconnect, status

from services.rag_service import RAGService
from middleware.rate_limiter import RateLimiter
from middleware.connection_manager import ConnectionManager


class ChatHandler:
    
    def __init__(
        self, 
        rag_service: RAGService,
        rate_limiter: RateLimiter,
        connection_manager: ConnectionManager
    ):
        self.rag = rag_service
        self.rate_limiter = rate_limiter
        self.conn_manager = connection_manager
    
    async def handle_connection(self, websocket: WebSocket):
        client_id = id(websocket)
        timeout_task = None

        if not await self.conn_manager.add_connection():
            print("Server: Connection rejected, limit reached")
            try:
                await websocket.close(
                    code=status.WS_1013_TRY_AGAIN_LATER, 
                    reason="Server capacity reached"
                )
            except Exception:
                pass
            return

        await websocket.accept()
        print(f"Server: Connected {client_id}")

        self.conn_manager.update_activity(client_id)
        timeout_task = asyncio.create_task(
            self.conn_manager.check_idle_timeout(websocket, client_id)
        )

        if not self.rag.llm or not self.rag.vectorstore:
            try:
                await websocket.send_json({
                    "answer": "Lỗi: Dịch vụ chưa sẵn sàng. Vui lòng thử lại sau.", 
                    "status": "error"
                })
                await websocket.close(code=1011)
            except Exception:
                pass
            return

        try:
            await self._chat_loop(websocket, client_id)
        except WebSocketDisconnect:
            print(f"Server: Disconnected {client_id}")
        except Exception as e:
            print(f"Server: Error {client_id} - {str(e)}")
            try:
                await websocket.send_json({
                    "answer": "Lỗi máy chủ. Vui lòng thử lại.", 
                    "status": "error"
                })
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            except Exception:
                pass
        finally:
            if timeout_task:
                timeout_task.cancel()
            await self.conn_manager.remove_connection(client_id)
            await self.rate_limiter.cleanup_client(client_id)

    async def _chat_loop(self, websocket: WebSocket, client_id: int):
        while True:
            data = await websocket.receive_text()
            self.conn_manager.update_activity(client_id)

            if not data.strip():
                continue

            if not await self.rate_limiter.check_rate_limit(websocket):
                continue

            answer = self.rag.generate_response(data)
            await websocket.send_json({
                "question": data, 
                "answer": answer.strip(), 
                "status": "success"
            })
