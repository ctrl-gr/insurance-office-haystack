from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.errors import register_exception_handlers
from backend.app.routes import chat_router, insurance_router, system_router
from backend.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="Haystack Insurance Office", version="4.0.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(application)
    application.include_router(system_router)
    application.include_router(insurance_router)
    application.include_router(chat_router)
    return application


app = create_app()
