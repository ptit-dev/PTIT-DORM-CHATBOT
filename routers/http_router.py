from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from dependency_injector.wiring import inject, Provide
from datetime import datetime
import asyncio


class PromptUpdateRequest(BaseModel):
    system_prompt: str


class PromptingItem(BaseModel):
    id: str
    type: str
    content: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PromptSyncRequest(BaseModel):
    prompting: List[PromptingItem]


class DocumentItem(BaseModel):
    id: str
    description: str
    content: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DatabaseSyncRequest(BaseModel):
    documents: List[DocumentItem]


class HTTPRouter:
    
    @inject
    def __init__(self,
                logging_service = Provide["Container.logging_service"],
                config = Provide["Container.config"],
                rag_service = Provide["Container.rag_service"],
                database_service = Provide["Container.db_service"],
                backend_api_service = Provide["Container.backend_api_service"],
                rate_limiter = Provide["Container.rate_limiter"],
                auth_middleware = Provide["Container.auth_middleware"]  
            ):
        self.logging_service = logging_service
        self.config = config
        self.rag_service = rag_service
        self.database_service = database_service
        self.backend_api_service = backend_api_service
        self.rate_limiter = rate_limiter
        self.logger = logging_service.get_logger(__name__)
        self.auth_middleware = auth_middleware
        self.router = APIRouter(prefix="/api", tags=["HTTP"])
        self._register_routes()
    
    def _register_routes(self):
        self.router.add_api_route("/health", self.health_check, methods=["GET"])
        
        self.router.add_api_route("/admin/prompt", self.get_prompt, methods=["GET"], dependencies=[Depends(self.auth_middleware.require_admin_auth)])
        self.router.add_api_route("/admin/prompt", self.update_prompt, methods=["PUT"], dependencies=[Depends(self.auth_middleware.require_admin_auth)])
        self.router.add_api_route("/admin/prompts/sync", self.sync_prompts_from_backend, methods=["POST"], dependencies=[Depends(self.auth_middleware.require_admin_auth)])
        self.router.add_api_route("/admin/database/sync", self.sync_vector_database, methods=["POST"], dependencies=[Depends(self.auth_middleware.require_admin_auth)])
        self.router.add_api_route("/admin/logs/download", self.download_logs, methods=["POST"], dependencies=[Depends(self.auth_middleware.require_admin_auth)])
        
        self.logger.info("HTTP router created with all endpoints")
    
    async def health_check(self):
        return {
            "status": "healthy",
            "service": "PTIT Dorm Chatbot"
        }

    async def get_prompt(self):
        return {"system_prompt": self.config.system_prompt}
    
    async def update_prompt(self, request: PromptUpdateRequest):
        self.config.system_prompt = request.system_prompt
        return {
            "status": "success",
            "message": "System prompt updated successfully",
            "system_prompt": self.config.system_prompt
        }
    
    async def sync_prompts_from_backend(self, request: PromptSyncRequest):
        try:
            guest_prompt = None
            for prompt in request.prompting:
                if prompt.type == 'guest':
                    guest_prompt = prompt
                    break
            
            if not guest_prompt:
                raise HTTPException(
                    status_code=400,
                    detail="No guest prompt found in request data"
                )
            
            try:
                self.config.system_prompt(guest_prompt.content)
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid system prompt: {str(e)}"
                )
            
            self.logger.info(f"System prompt synced: type={guest_prompt.type}, id={guest_prompt.id}")
            
            return {
                "status": "success",
                "message": "Prompt synced successfully",
                "prompt": {
                    "id": guest_prompt.id,
                    "type": guest_prompt.type,
                    "updated_at": guest_prompt.updated_at
                }
            }
                
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error syncing prompts: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error syncing prompts: {str(e)}"
            )
    
    async def sync_vector_database(self, request: DatabaseSyncRequest):
        try:
            if not request.documents:
                raise HTTPException(
                    status_code=400,
                    detail="No documents found in request data"
                )
            
            documents_data = [
                {
                    "id": doc.id,
                    "description": doc.description,
                    "content": doc.content,
                    "created_at": doc.created_at,
                    "updated_at": doc.updated_at
                }
                for doc in request.documents
            ]
            
            self.database_service.set_documents_from_backend(documents_data)
            self.logger.info(f"Received {len(documents_data)} documents from backend")
            
            vectorstore = self.database_service.setup_database()
            
            if vectorstore:
                self.rag_service.vectorstore = vectorstore
                self.logger.info(f"Vector database rebuilt with {len(documents_data)} documents")
                
                return {
                    "status": "success",
                    "message": "Vector database synced successfully",
                    "documents_count": len(documents_data)
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to rebuild vector database"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error syncing database: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error syncing database: {str(e)}"
            )
    
    async def download_logs(self, download_all: bool = Query(False, description="Download all logs as zip")):
        try:
            if download_all:
                archive_path = self.logging_service.create_logs_archive("logs_download.zip")
                
                response = FileResponse(
                    path=str(archive_path),
                    filename=f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    media_type="application/zip"
                )
                
                async def cleanup():
                    await asyncio.sleep(3)
                    self.logging_service.cleanup_temp_archive(archive_path)
                
                asyncio.create_task(cleanup())
                
                return response
            else:
                log_path = self.logging_service.get_latest_log_path()
                
                if not log_path.exists():
                    raise HTTPException(status_code=404, detail="No log files found")
                
                return FileResponse(
                    path=str(log_path),
                    filename=f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                    media_type="text/plain"
                )
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error downloading logs: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error downloading logs: {str(e)}"
            )
