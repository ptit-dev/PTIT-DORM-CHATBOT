import time
import asyncio
from typing import Dict, List
from fastapi import WebSocket


class RateLimiter:
    
    def __init__(self, max_messages: int = 1, time_window_seconds: int = 10):
        self.max_messages = max_messages
        self.time_window_seconds = time_window_seconds
        self._store: Dict[int, List[float]] = {}
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(self, websocket: WebSocket) -> bool:
        client_id = id(websocket)
        current_time = time.time()

        async with self._lock:
            timestamps = [
                t for t in self._store.get(client_id, []) 
                if t > current_time - self.time_window_seconds
            ]

            if len(timestamps) >= self.max_messages:
                time_to_wait = (timestamps[0] + self.time_window_seconds) - current_time
                print(f"RateLimit: {client_id} exceeded, wait {time_to_wait:.1f}s")

                try:
                    await websocket.send_json({
                        "answer": "Bạn gửi quá nhanh, vui lòng chờ một chút trước khi gửi câu hỏi tiếp theo.",
                        "status": "rate_limited"
                    })
                except Exception:
                    pass
                return False

            timestamps.append(current_time)
            self._store[client_id] = timestamps
            return True
    
    async def cleanup_client(self, client_id: int):
        async with self._lock:
            self._store.pop(client_id, None)
    
    @property
    def client_count(self) -> int:
        return len(self._store)
