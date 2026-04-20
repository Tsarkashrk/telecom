from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_internal_service
from app.logging_config import AuditAction, log_audit, log_security_event
from app.models import Invoice, Subscription, TariffPlan
from app.schemas import InvoiceResponse

router = APIRouter()


@router.post(
    "/subscriptions/{subscription_id}/generate-invoice",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED
)
def generate_next_invoice(
    subscription_id: int,
    service_name: str = Depends(get_internal_service),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None)
):
    """
    Внутренний billing API для генерации следующего счета.

    Логика:
    - работает только для активной подписки;
    - недоступен клиентам, операторам и администраторам по JWT;
    - защищен отдельным internal API key;
    - предотвращает создание дубля счета на тот же billing period.
    """
    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "internal"

    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id
    ).first()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подписка не найдена"
        )

    if not subscription.is_active or subscription.status != "active":
        log_security_event(
            event_type="internal_billing_generation_failed",
            user_id=subscription.user_id,
            reason=f"Subscription {subscription_id} is not active",
            severity="WARNING",
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Счет можно создать только для активной подписки"
        )

    tariff = db.query(TariffPlan).filter(TariffPlan.id == subscription.tariff_id).first()
    if not tariff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тариф подписки не найден"
        )

    billing_period_start = subscription.next_billing_date
    billing_period_end = billing_period_start + timedelta(days=30)

    existing_invoice = db.query(Invoice).filter(
        Invoice.subscription_id == subscription.id,
        Invoice.billing_period_start == billing_period_start,
        Invoice.billing_period_end == billing_period_end
    ).first()
    if existing_invoice:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Счет за этот период уже создан"
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    invoice = Invoice(
        user_id=subscription.user_id,
        subscription_id=subscription.id,
        amount=tariff.monthly_price,
        status="pending",
        billing_period_start=billing_period_start,
        billing_period_end=billing_period_end,
        due_date=now + timedelta(days=10),
        created_at=now
    )

    db.add(invoice)
    subscription.next_billing_date = billing_period_end
    db.commit()
    db.refresh(invoice)

    log_audit(
        action=AuditAction.INVOICE_CREATED,
        user_id=subscription.user_id,
        details=f"{service_name} generated invoice {invoice.id} for subscription {subscription.id}",
        ip_address=client_ip,
        success=True
    )

    return invoice
