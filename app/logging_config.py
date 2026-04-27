import logging
from enum import Enum

from sqlalchemy.exc import SQLAlchemyError

from app import database
from app.models import AuditLog

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


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
        db = database.SessionLocal()
        audit_record = AuditLog(
            user_id=user_id,
            action=action[:100],
            action_details=details,
            ip_address=ip_address,
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
    log_message = f"[AUDIT] Action: {action.value}"
    
    if user_id:
        log_message += f" | User ID: {user_id}"
    if ip_address:
        log_message += f" | IP: {ip_address}"
    if details:
        log_message += f" | Details: {details}"
    
    log_message += f" | Success: {success}"
    
    if success:
        logger.info(log_message)
    else:
        logger.warning(log_message)

    _persist_audit_record(
        action=action.value,
        user_id=user_id,
        details=details,
        ip_address=ip_address,
        success=success
    )


def log_security_event(
    event_type: str,
    user_id: int | None = None,
    reason: str | None = None,
    severity: str = "WARNING",
    ip_address: str | None = None
) -> None:
    log_message = f"[SECURITY] Event: {event_type}"
    
    if user_id:
        log_message += f" | User ID: {user_id}"
    if ip_address:
        log_message += f" | IP: {ip_address}"
    if reason:
        log_message += f" | Reason: {reason}"
    
    if severity == "CRITICAL":
        logger.critical(log_message)
    elif severity == "ERROR":
        logger.error(log_message)
    else:
        logger.warning(log_message)

    _persist_audit_record(
        action=f"security:{event_type}",
        user_id=user_id,
        details=reason,
        ip_address=ip_address,
        success=False
    )
