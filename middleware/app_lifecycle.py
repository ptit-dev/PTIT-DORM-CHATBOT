import asyncio
from services.rag_service import RAGService
from services.database_service import DatabaseService
from middleware.connection_manager import ConnectionManager
from services.config_service import config_service


class AppLifecycle:
    
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
        self.config = config_service
    
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
            await asyncio.sleep(self.config.status_interval)
            print(f"Status: Connections = {self.conn_manager.active_connections}")
    
    async def auto_reload(self):
        while True:
            await asyncio.sleep(self.config.reload_interval)
            
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

    async def reload_dorm_stats(self):
        async with self._reload_lock:
            if self._is_reloading:
                return {"status": "error", "message": "Reload is already in progress"}
            self._is_reloading = True

        try:
            print("Server: Reloading dorm stats")
            token = await asyncio.to_thread(self.db.get_access_token)
            if token:
                await asyncio.to_thread(self.db.generate_report, token)
                await asyncio.to_thread(self.db.setup_database)
                self.rag.load_llm_and_db()
                print("Server: dorm stats reload done")
                return {"status": "success", "message": "dorm statistics reloaded successfully"}
            else:
                return {"status": "error", "message": "Cannot get access token"}
        except Exception as e:
            print(f"Server: dorm stats reload error - {e}")
            return {"status": "error", "message": str(e)}
        finally:
            async with self._reload_lock:
                self._is_reloading = False

    async def reload_database(self):
        async with self._reload_lock:
            if self._is_reloading:
                return {"status": "error", "message": "Reload is already in progress"}
            self._is_reloading = True

        try:
            print("Server: Reloading database")
            await asyncio.to_thread(self.db.setup_database)
            self.rag.load_llm_and_db()
            print("Server: Database reload done")
            return {"status": "success", "message": "Database reloaded successfully"}
        except Exception as e:
            print(f"Server: Database reload error - {e}")
            return {"status": "error", "message": str(e)}
        finally:
            async with self._reload_lock:
                self._is_reloading = False
