from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError
import logging
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.database import engine
from app.models import Base
from app.routers import auth, subscriptions, invoices, internal_billing
from app.config import settings
from app.logging_config import log_security_event
from app.db_security import migrate_user_passwords

logger = logging.getLogger(__name__)


class RequestSizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_size: int):
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1"): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        content_length = headers.get("content-length")

        if content_length is not None:
            try:
                if int(content_length) > self.max_body_size:
                    await self._send_413(scope, send)
                    return
            except ValueError:
                await self._send_400(scope, send)
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()

            if message["type"] != "http.request":
                return message

            body = message.get("body", b"")
            received += len(body)
            if received > self.max_body_size:
                raise RequestSizeExceededError

            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestSizeExceededError:
            await self._send_413(scope, send)

    async def _send_400(self, scope: Scope, send: Send) -> None:
        response = JSONResponse(
            status_code=400,
            content={"error": "Некорректный заголовок Content-Length"},
        )
        await response(scope, self._empty_receive, send)

    async def _send_413(self, scope: Scope, send: Send) -> None:
        response = JSONResponse(
            status_code=413,
            content={"error": "Размер запроса превышает допустимый предел"},
        )
        await response(scope, self._empty_receive, send)

    async def _empty_receive(self) -> Message:
        return {"type": "http.disconnect"}


class RequestSizeExceededError(Exception):
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    Base.metadata.create_all(bind=engine)
    migrate_user_passwords(engine)
    yield
    logger.info("Application shutdown")
app = FastAPI(
    title="Телекоммуникационная платформа AI-Assisted",
    description="AI-assisted версия системы регистрации клиентов и биллинга с аутентификацией и авторизацией",
    version="2.0.0-ai",
    lifespan=lifespan
)
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_body_size=settings.max_request_size_bytes
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
        "name": "Telecom AI-Assisted API",
        "version": "2.0.0-ai",
        "status": "running"
    }


@app.get("/health", tags=["Информация"])
async def health_check():
    return {"status": "healthy"}

# vul: if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
