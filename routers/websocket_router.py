from fastapi import APIRouter, WebSocket
from dependency_injector.wiring import inject, Provide


class WebSocketRouter:
    
    @inject
    def __init__(self,
                 chat_handler = Provide["Container.chat_handler"],
                 log_stream_handler = Provide["Container.log_stream_handler"],
                 logging_service = Provide["Container.logging_service"]):
        self.chat_handler = chat_handler
        self.log_stream_handler = log_stream_handler
        self.logger = logging_service.get_logger(__name__)
        
        self.router = APIRouter(tags=["WebSocket"])
        self._register_routes()
    
    def _register_routes(self):
        self.router.add_api_websocket_route("/ws/chat", self.websocket_chat)
        self.router.add_api_websocket_route("/ws/logs", self.websocket_logs)
        
        self.logger.info("WebSocket router created with chat and log streaming")
    
    async def websocket_chat(self, websocket: WebSocket):
        await self.chat_handler.handle_chat(websocket)
    
    async def websocket_logs(self, websocket: WebSocket):
        await self.log_stream_handler.stream_logs(websocket)
