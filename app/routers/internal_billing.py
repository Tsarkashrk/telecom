from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_internal_service
from app.logging_config import AuditAction, log_audit, log_security_event
from app.models import Invoice, Subscription
from app.schemas import InvoiceResponse

router = APIRouter()


@router.post("/users/{user_id}/generate-invoice", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def generate_invoice_for_user(
    user_id: int,
    service_name: str = Depends(get_internal_service),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None)
):
    """
    Внутренний billing API для генерации счета по активной подписке клиента.

    Требования безопасности:
    - endpoint изолирован в отдельном internal router;
    - доступ только по service-to-service API key;
    - не используется пользовательская JWT-аутентификация;
    - все обращения журналируются.
    """
    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "internal"

    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.is_active == True
    ).first()

    if not subscription or not subscription.tariff_plan:
        log_security_event(
            event_type="internal_billing_generation_failed",
            reason=f"No active subscription for user {user_id}",
            severity="WARNING"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Активная подписка не найдена"
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    billing_period_end = subscription.next_billing_date

    invoice = Invoice(
        user_id=user_id,
        subscription_id=subscription.id,
        amount=subscription.tariff_plan.monthly_price,
        status="pending",
        billing_period_start=now,
        billing_period_end=billing_period_end,
        due_date=now + timedelta(days=10),
        created_at=now
    )

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    log_audit(
        action=AuditAction.INVOICE_CREATED,
        user_id=user_id,
        details=f"{service_name} generated invoice {invoice.id}",
        ip_address=client_ip,
        success=True
    )

    return invoice
