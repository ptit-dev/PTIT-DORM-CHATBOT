import os
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv

load_dotenv()

API_KEY_HEADER = APIKeyHeader(name="API-key", auto_error=False)
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")


async def require_admin_auth(api_key: Optional[str] = Security(API_KEY_HEADER)) -> bool:
    if api_key and api_key == ADMIN_API_KEY:
        return True
    
    raise HTTPException(
        status_code=401,
        detail="Unauthorized. Provide valid key header."
    )
