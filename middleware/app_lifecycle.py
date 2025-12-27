import asyncio
from services.rag_service import RAGService
from services.database_service import DatabaseService
from middleware.connection_manager import ConnectionManager


class AppLifecycle:
    
    RELOAD_INTERVAL = 3 * 24 * 60 * 60
    STATUS_INTERVAL = 60 * 10
    
    def __init__(
        self, 
        rag_service: RAGService, 
        db_service: DatabaseService,
        connection_manager: ConnectionManager
    ):
        self.rag = rag_service
        self.db = db_service
        self.conn_manager = connection_manager
        self._is_reloading = False
        self._reload_lock = asyncio.Lock()
    
    async def startup(self):
        print("Server: Starting")
        await asyncio.to_thread(self.db.setup_database)
        self.rag.load_llm_and_db()

        if self.rag.llm and self.rag.vectorstore:
            print("Server: Ready")
        else:
            print("Server: Init failed")

        asyncio.create_task(self.status_reporter())
        asyncio.create_task(self.auto_reload())
    
    async def status_reporter(self):
        while True:
            await asyncio.sleep(self.STATUS_INTERVAL)
            print(f"Status: Connections = {self.conn_manager.active_connections}")
    
    async def auto_reload(self):
        while True:
            await asyncio.sleep(self.RELOAD_INTERVAL)
            
            async with self._reload_lock:
                if self._is_reloading:
                    continue
                self._is_reloading = True

            try:
                print("Server: Reloading DB")
                await asyncio.to_thread(self.db.setup_database)
                self.rag.load_llm_and_db()
                print("Server: Reload done")
            except Exception as e:
                print(f"Server: Reload error - {e}")
            finally:
                async with self._reload_lock:
                    self._is_reloading = False
