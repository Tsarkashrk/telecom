from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.database import engine
from app.models import Base
from app.routers import auth, subscriptions, invoices, internal_billing
from app.logging_config import log_security_event

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")
app = FastAPI(
    title="Телекоммуникационная платформа MVP",
    description="Система регистрации клиентов и биллинга с аутентификацией и авторизацией",
    version="1.0.0",
    lifespan=lifespan
)
app.include_router(auth.router, prefix="/api/auth", tags=["Аутентификация"])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["Подписки"])
app.include_router(invoices.router, prefix="/api/billing", tags=["Биллинг"])
app.include_router(
    internal_billing.router,
    prefix="/api/internal/billing",
    tags=["Внутренний биллинг"]
)
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.exception("Database error")
    log_security_event(
        event_type="database_error",
        # Безопаснее не писать клиенту и в аудит полный текст SQL-ошибки.

        # vul: return JSONResponse(status_code=500, content={"error": str(exc)})
        reason=exc.__class__.__name__,
        severity="ERROR"
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Внутренняя ошибка сервера"}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 400:
        client_ip = request.headers.get("x-forwarded-for", "unknown")
        if exc.status_code == 401 or exc.status_code == 403:
            log_security_event(
                event_type="http_error",
                reason=f"Status {exc.status_code}: {exc.detail}",
                severity="WARNING"
            )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.get("/", tags=["Информация"])
async def root():
    return {
        "name": "Telecom MVP",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", tags=["Информация"])
async def health_check():
    return {"status": "healthy"}

# vul: if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
