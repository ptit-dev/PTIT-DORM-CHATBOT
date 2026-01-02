from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional

from services.config_service import config_service
from services.file_service import file_service
from services.rag_service import RAGService
from middleware.app_lifecycle import AppLifecycle
from middleware.auth import require_admin_auth


class PromptUpdateRequest(BaseModel):
    system_prompt: str


class AdminRouter:
    
    def __init__(self, lifecycle: AppLifecycle, rag_service: RAGService):
        self.lifecycle = lifecycle
        self.rag_service = rag_service
        self.router = APIRouter(prefix="/api", tags=["Admin"], dependencies=[Depends(require_admin_auth)])
        self.register_routes()
    
    def register_routes(self):
        self.router.add_api_route("/prompt", self.get_prompt, methods=["GET"])
        self.router.add_api_route("/prompt", self.update_prompt, methods=["PUT"])
        self.router.add_api_route("/reload-dorm-stats", self.reload_dorm_stats, methods=["POST"])
        self.router.add_api_route("/add-txt", self.add_txt_file, methods=["POST"])
        self.router.add_api_route("/delete-txt/{filename}", self.delete_txt_file, methods=["DELETE"])
        self.router.add_api_route("/reset-data", self.reset_data, methods=["POST"])
        self.router.add_api_route("/txt-files", self.list_txt_files, methods=["GET"])

    async def get_prompt(self):
        return {"system_prompt": config_service.system_prompt}

    async def update_prompt(self, request: PromptUpdateRequest):
        config_service.system_prompt = request.system_prompt
        return {"status": "success", "message": "System prompt updated successfully", "system_prompt": config_service.system_prompt}

    async def reload_dorm_stats(self):
        result = await self.lifecycle.reload_dorm_stats()
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        return result

    async def add_txt_file(self, file: UploadFile = File(...)):
        try:
            filename = await file_service.add_txt_file(file)
            result = await self.lifecycle.reload_database()
            return {"status": "success", "message": f"File '{filename}' added successfully", "reload_result": result}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except FileExistsError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def delete_txt_file(self, filename: str):
        try:
            file_service.delete_txt_file(filename)
            result = await self.lifecycle.reload_database()
            return {"status": "success", "message": f"File '{filename}' deleted successfully", "reload_result": result}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def reset_data(self):
        try:
            reset_result = file_service.reset_all_data()
            reload_result = await self.lifecycle.reload_database()
            return {
                "status": "success", 
                "message": "All TXT files and database reset successfully", 
                "reset_result": reset_result,
                "reload_result": reload_result
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def list_txt_files(self):
        try:
            files = file_service.list_txt_files()
            return {"files": files}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
