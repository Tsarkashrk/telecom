import logging
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from app import database
from app.config import settings
from app.input_security import sanitize_log_value
from app.models import AuditLog

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format=LOG_FORMAT
)

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("app.audit")


def configure_audit_logging(log_file_path: str | None = None) -> logging.Logger:
    target_path = Path(log_file_path or settings.audit_log_file).expanduser()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_target = target_path.resolve()

    for handler in list(audit_logger.handlers):
        if isinstance(handler, RotatingFileHandler):
            current_path = Path(handler.baseFilename).resolve()
            if current_path == resolved_target:
                return audit_logger
            audit_logger.removeHandler(handler)
            handler.close()

    file_handler = RotatingFileHandler(
        resolved_target,
        maxBytes=settings.audit_log_max_bytes,
        backupCount=settings.audit_log_backup_count,
        encoding="utf-8"
    )
    file_handler.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    audit_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    audit_logger.addHandler(file_handler)
    audit_logger.propagate = True
    return audit_logger


configure_audit_logging()


class AuditAction(str, Enum):
    USER_REGISTERED = "user_registered"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    TARIFF_ACTIVATED = "tariff_activated"
    INVOICE_CREATED = "invoice_created"
    INVOICE_PAID = "invoice_paid"
    INVOICE_VIEWED = "invoice_viewed"
    SUBSCRIPTION_VIEWED = "subscription_viewed"
    UNAUTHORIZED_ACCESS_ATTEMPT = "unauthorized_access_attempt" 
    INVALID_TOKEN = "invalid_token" # nosec
    PASSWORD_CHANGED = "password_changed" # nosec


def _persist_audit_record(
    action: str,
    user_id: int | None = None,
    details: str | None = None,
    ip_address: str | None = None,
    success: bool = True
) -> None:
    db = None
    try:
        sanitized_action = sanitize_log_value(action, max_length=100) or "unknown"
        sanitized_details = sanitize_log_value(details)
        sanitized_ip = sanitize_log_value(ip_address, max_length=50)
        db = database.SessionLocal()
        audit_record = AuditLog(
            user_id=user_id,
            action=sanitized_action,
            action_details=sanitized_details,
            ip_address=sanitized_ip,
            success=success
        )
        db.add(audit_record)
        db.commit()
    except SQLAlchemyError as exc:
        logger.error(f"Failed to persist audit record: {exc.__class__.__name__}")
        if db is not None:
            db.rollback()
    finally:
        if db is not None:
            db.close()


def log_audit(
    action: AuditAction,
    user_id: int | None = None,
    details: str | None = None,
    ip_address: str | None = None,
    success: bool = True
) -> None:
    sanitized_ip = sanitize_log_value(ip_address, max_length=50)
    sanitized_details = sanitize_log_value(details)
    log_message = f"[AUDIT] Action: {action.value}"
    
    if user_id:
        log_message += f" | User ID: {user_id}"
    if sanitized_ip:
        log_message += f" | IP: {sanitized_ip}"
    if sanitized_details:
        log_message += f" | Details: {sanitized_details}"
    
    log_message += f" | Success: {success}"
    
    if success:
        audit_logger.info(log_message)
    else:
        audit_logger.warning(log_message)

    _persist_audit_record(
        action=action.value,
        user_id=user_id,
        details=sanitized_details,
        ip_address=sanitized_ip,
        success=success
    )


def log_security_event(
    event_type: str,
    user_id: int | None = None,
    reason: str | None = None,
    severity: str = "WARNING",
    ip_address: str | None = None
) -> None:
    sanitized_event_type = sanitize_log_value(event_type, max_length=100) or "unknown"
    sanitized_reason = sanitize_log_value(reason)
    sanitized_ip = sanitize_log_value(ip_address, max_length=50)
    log_message = f"[SECURITY] Event: {sanitized_event_type}"
    
    if user_id:
        log_message += f" | User ID: {user_id}"
    if sanitized_ip:
        log_message += f" | IP: {sanitized_ip}"
    if sanitized_reason:
        log_message += f" | Reason: {sanitized_reason}"
    
    if severity == "CRITICAL":
        audit_logger.critical(log_message)
    elif severity == "ERROR":
        audit_logger.error(log_message)
    else:
        audit_logger.warning(log_message)

    _persist_audit_record(
        action=f"security:{sanitized_event_type}",
        user_id=user_id,
        details=sanitized_reason,
        ip_address=sanitized_ip,
        success=False
    )
