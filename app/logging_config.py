import logging
from datetime import datetime
from enum import Enum

from app.database import SessionLocal
from app.models import AuditLog

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Типы действий для аудита"""
    USER_REGISTERED = "user_registered"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    TARIFF_ACTIVATED = "tariff_activated"
    INVOICE_CREATED = "invoice_created"
    INVOICE_PAID = "invoice_paid"
    INVOICE_VIEWED = "invoice_viewed"
    SUBSCRIPTION_VIEWED = "subscription_viewed"
    UNAUTHORIZED_ACCESS_ATTEMPT = "unauthorized_access_attempt"
    INVALID_TOKEN = "invalid_token"
    PASSWORD_CHANGED = "password_changed"


def _persist_audit_record(
    action: str,
    user_id: int = None,
    details: str = None,
    ip_address: str = None,
    success: bool = True
) -> None:
    """
    Сохраняет запись аудита в БД.

    Ошибка аудита не должна ломать бизнес-операцию, поэтому
    исключения только журналируются.
    """
    db = None
    try:
        db = SessionLocal()
        audit_record = AuditLog(
            user_id=user_id,
            action=action[:100],
            action_details=details,
            ip_address=ip_address,
            success=success
        )
        db.add(audit_record)
        db.commit()
    except Exception as exc:
        logger.error(f"Failed to persist audit record: {exc}")
        if db is not None:
            db.rollback()
    finally:
        if db is not None:
            db.close()


def log_audit(
    action: AuditAction,
    user_id: int = None,
    details: str = None,
    ip_address: str = None,
    success: bool = True
) -> None:
    """
    Логирование критичных действий без чувствительных данных.
    
    ВАЖНО: Никогда не логируем пароли, токены, полные номера счетов.
    """
    log_message = f"[AUDIT] Action: {action.value}"
    
    if user_id:
        log_message += f" | User ID: {user_id}"
    if ip_address:
        log_message += f" | IP: {ip_address}"
    if details:
        # Убедитесь, что details не содержит чувствительных данных
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
    user_id: int = None,
    reason: str = None,
    severity: str = "WARNING",
    ip_address: str = None
) -> None:
    """Логирование событий безопасности"""
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
