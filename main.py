from fastapi import FastAPI
from common.container import Container
from middleware.cors import setup_cors

container = Container()
container.wire()

app_lifecycle = container.app_lifecycle()
http_router_handler = container.http_router()
websocket_router_handler = container.websocket_router()
logging_service = container.logging_service()
logger = logging_service.get_logger(__name__)

app = FastAPI(title="PTIT Dorm Chatbot API", version="1.0.0")
setup_cors(app)

app.include_router(http_router_handler.router)
app.include_router(websocket_router_handler.router)


@app.on_event("startup")
async def startup():
    logger.info("Application starting...")
    await app_lifecycle.startup()
    logger.info("✓ Application ready")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutting down...")
    await app_lifecycle.shutdown()
    logger.info("✓ Application stopped")
