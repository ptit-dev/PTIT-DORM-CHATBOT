import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import WebSocket, WebSocketDisconnect
from dependency_injector.wiring import inject, Provide


class LogStreamHandler:
    
    @inject
    def __init__(self, 
        logging_service = Provide["Container.logging_service"],
        config = Provide["Container.config"]
    ):
        self.logger = logging_service.get_logger(__name__)
        self.logging_service = logging_service
        self.config = config
        self.logs_dir = Path("logs")
    
    async def stream_logs(self, websocket: WebSocket):
        await websocket.accept()
        
        try:
            auth_data = await websocket.receive_json()
            
            api_key = auth_data.get("api_key", "")
            
            if not api_key or api_key != self.config.admin_api_key:
                await websocket.send_json({
                    "error": "Unauthorized",
                    "message": "Invalid API key"
                })
                await websocket.close(code=1008)
                return
            
            minutes = auth_data.get("minutes", 10)
            
            await websocket.send_json({
                "status": "connected",
                "message": f"Streaming logs from last {minutes} minutes"
            })
            
            vietnam_tz = timezone(timedelta(hours=7))
            start_time = datetime.now(vietnam_tz) - timedelta(minutes=minutes)
            
            log_path = self.logging_service.get_latest_log_path()
            
            if not log_path.exists():
                await websocket.send_json({
                    "error": "Not Found",
                    "message": "No log files found"
                })
                await websocket.close()
                return
            
            await self._send_historical_logs(websocket, log_path, start_time)
            
            await self._tail_log_file(websocket, log_path)
            
        except WebSocketDisconnect:
            self.logger.info("WebSocket client disconnected")
        except Exception as e:
            self.logger.error(f"Error in log streaming: {str(e)}")
            try:
                await websocket.send_json({
                    "error": "Internal Error",
                    "message": str(e)
                })
            except:
                pass
            await websocket.close()
    
    async def _send_historical_logs(self, websocket: WebSocket, log_path: Path, start_time: datetime):
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('['):
                        try:
                            timestamp_str = line[1:20]  
                            log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            vietnam_tz = timezone(timedelta(hours=7))
                            log_time = log_time.replace(tzinfo=vietnam_tz)
                            
                            if log_time >= start_time:
                                await websocket.send_json({
                                    "type": "log",
                                    "content": line.rstrip('\n')
                                })
                        except ValueError:
                            await websocket.send_json({
                                "type": "log",
                                "content": line.rstrip('\n')
                            })
                    else:
                        await websocket.send_json({
                            "type": "log",
                            "content": line.rstrip('\n')
                        })
            
            await websocket.send_json({
                "type": "marker",
                "message": "Historical logs sent, now tailing..."
            })
            
        except Exception as e:
            self.logger.error(f"Error sending historical logs: {str(e)}")
            raise
    
    async def _tail_log_file(self, websocket: WebSocket, log_path: Path):
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                f.seek(0, 2)
                
                while True:
                    line = f.readline()
                    
                    if line:
                        await websocket.send_json({
                            "type": "log",
                            "content": line.rstrip('\n')
                        })
                    else:
                        await asyncio.sleep(0.5)
                        
                        if not log_path.exists():
                            await websocket.send_json({
                                "type": "info",
                                "message": "Log file rotated, reconnect to continue"
                            })
                            break
        
        except Exception as e:
            self.logger.error(f"Error tailing log file: {str(e)}")
            raise
