from dependency_injector import containers, providers
from .config import Config
from services.logging_service import LoggingService
from services.rag_service import RAGService
from services.database_service import DatabaseService
from services.backend_api_service import BackendAPIService
from handler.connection_manager import ConnectionManager
from middleware.rate_limiter import RateLimiter
from handler.app_lifecycle import AppLifecycle
from handler.chat_handler import ChatHandler
from handler.log_stream_handler import LogStreamHandler
from routers.http_router import HTTPRouter
from routers.websocket_router import WebSocketRouter
from middleware.auth import AuthMiddleware


class Container(containers.DeclarativeContainer):
    
    wiring_config = containers.WiringConfiguration(
        modules=[
            "main",
            "middleware.auth",
            "handler.app_lifecycle",
            "handler.chat_handler",
            "handler.log_stream_handler",
            "services.rag_service",
            "services.database_service",
            "services.backend_api_service",
            "routers.http_router",
            "routers.websocket_router",
        ]
    )

    config = providers.ThreadSafeSingleton(Config)
    
    logging_service = providers.ThreadSafeSingleton(LoggingService)

    auth_middleware = providers.ThreadSafeSingleton(
        AuthMiddleware,
        config=config
    )

    backend_api_service = providers.ThreadSafeSingleton(
        BackendAPIService,
        config=config,
        logging_service=logging_service
    )

    db_service = providers.ThreadSafeSingleton(
        DatabaseService,
        config=config,
        logging_service=logging_service
    )

    rag_service = providers.ThreadSafeSingleton(
        RAGService,
        config=config,
        logging_service=logging_service
    )

    connection_manager = providers.ThreadSafeSingleton(
        ConnectionManager,
        max_connections=config.provided.max_connections,
        idle_timeout_seconds=config.provided.idle_timeout_seconds
    )

    rate_limiter = providers.ThreadSafeSingleton(
        RateLimiter,
        max_messages=config.provided.max_messages,
        time_window_seconds=config.provided.time_window_seconds
    )

    chat_handler = providers.ThreadSafeSingleton(
        ChatHandler,
        rag_service=rag_service,
        logging_service=logging_service,
        rate_limiter=rate_limiter,
        connection_manager=connection_manager
    )

    app_lifecycle = providers.ThreadSafeSingleton(
        AppLifecycle,
        rag_service=rag_service,
        db_service=db_service,
        config=config,
        logging_service=logging_service,
        connection_manager=connection_manager,
        backend_api_service=backend_api_service
    )

    log_stream_handler = providers.ThreadSafeSingleton(
        LogStreamHandler,
        logging_service=logging_service,
        config=config
    )

    http_router = providers.ThreadSafeSingleton(
        HTTPRouter,
        logging_service=logging_service,
        config=config,
        rag_service=rag_service,
        database_service=db_service,
        backend_api_service=backend_api_service,
        rate_limiter=rate_limiter,
        auth_middleware=auth_middleware
    )
    
    websocket_router = providers.ThreadSafeSingleton(
        WebSocketRouter,
        logging_service=logging_service,
        chat_handler=chat_handler,
        log_stream_handler=log_stream_handler
    )