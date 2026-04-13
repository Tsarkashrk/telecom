import logging
from datetime import datetime
from enum import Enum

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
    INVOICE_VIEWED = "invoice_viewed"
    UNAUTHORIZED_ACCESS_ATTEMPT = "unauthorized_access_attempt"
    INVALID_TOKEN = "invalid_token"
    PASSWORD_CHANGED = "password_changed"


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


def log_security_event(
    event_type: str,
    user_id: int = None,
    reason: str = None,
    severity: str = "WARNING"
) -> None:
    """Логирование событий безопасности"""
    log_message = f"[SECURITY] Event: {event_type}"
    
    if user_id:
        log_message += f" | User ID: {user_id}"
    if reason:
        log_message += f" | Reason: {reason}"
    
    if severity == "CRITICAL":
        logger.critical(log_message)
    elif severity == "ERROR":
        logger.error(log_message)
    else:
        logger.warning(log_message)
