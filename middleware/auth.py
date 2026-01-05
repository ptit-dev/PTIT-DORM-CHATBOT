from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from dependency_injector.wiring import inject, Provide

API_KEY_HEADER = APIKeyHeader(name="API-key", auto_error=False)

class AuthMiddleware:
    
    @inject
    def __init__(self, config = Provide["config"]):
        self.config = config
    
    async def require_admin_auth(
        self,
        api_key: Optional[str] = Security(API_KEY_HEADER)
    ) -> bool:
        if api_key and api_key == self.config.admin_api_key: 
            return True
        
        raise HTTPException(
            status_code=401,
            detail="Unauthorized. Provide valid key header."
        )