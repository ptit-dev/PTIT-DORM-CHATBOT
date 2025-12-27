import time
import asyncio
from typing import Dict
from fastapi import WebSocket, status


class ConnectionManager:
    def __init__(self, max_connections: int = 100, idle_timeout_seconds: int = 30):
        self.max_connections = max_connections
        self.idle_timeout_seconds = idle_timeout_seconds
        self._active_count = 0
        self._last_activity: Dict[int, float] = {}
        self._lock = asyncio.Lock()
    
    async def can_accept_connection(self) -> bool:
        async with self._lock:
            return self._active_count < self.max_connections
    
    async def add_connection(self) -> bool:
        async with self._lock:
            if self._active_count >= self.max_connections:
                return False
            self._active_count += 1
            return True
    
    async def remove_connection(self, client_id: int):
        async with self._lock:
            self._active_count = max(0, self._active_count - 1)
            self._last_activity.pop(client_id, None)
    
    def update_activity(self, client_id: int):
        self._last_activity[client_id] = time.time()
    
    async def check_idle_timeout(self, websocket: WebSocket, client_id: int):
        while True:
            await asyncio.sleep(10)

            if websocket.client_state != status.WS_CONNECTED:
                break

            last_activity_time = self._last_activity.get(client_id, time.time())
            current_time = time.time()

            if (current_time - last_activity_time) > self.idle_timeout_seconds:
                print(f"Conn: {client_id} idle, disconnecting")
                try:
                    await websocket.send_json({
                        "answer": f"Kết nối đã bị ngắt do không hoạt động trong {self.idle_timeout_seconds} giây.", 
                        "status": "timeout"
                    })
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                except Exception:
                    pass
                break
    
    @property
    def active_connections(self) -> int:
        return self._active_count
    
    @property
    def activity_count(self) -> int:
        return len(self._last_activity)
