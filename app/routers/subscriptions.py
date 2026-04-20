from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.database import get_db
from app.models import User, Subscription, TariffPlan, Invoice
from app.schemas import (
    SubscriptionResponse, ActivateTariffRequest,
    TariffPlanResponse, InvoiceResponse, ErrorResponse
)
from app.dependencies import get_current_user, get_current_operator, verify_object_access
from app.logging_config import log_audit, log_security_event, AuditAction

router = APIRouter()


@router.get("/tariffs", response_model=List[TariffPlanResponse])
def get_available_tariffs(db: Session = Depends(get_db)):
    tariffs = db.query(TariffPlan).filter(TariffPlan.is_active == True).all()
    return tariffs


@router.post("/activate", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def activate_tariff(
    request: ActivateTariffRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None)
):
    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "unknown"
    tariff = db.query(TariffPlan).filter(
        and_(TariffPlan.id == request.tariff_id, TariffPlan.is_active == True)
    ).first()
    
    if not tariff:
        log_security_event(
            event_type="invalid_tariff_activation",
            user_id=current_user.id,
            reason=f"Tariff ID {request.tariff_id} not found",
            severity="WARNING"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тариф не найден"
        )
    existing_subscription = db.query(Subscription).filter(
        and_(
            Subscription.user_id == current_user.id,
            Subscription.status.in_(["pending_payment", "active"])
        )
    ).first()
    
    if existing_subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя уже есть активная или ожидающая оплаты подписка"
        )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    next_billing = now + timedelta(days=30)
    
    subscription = Subscription(
        user_id=current_user.id,
        tariff_id=tariff.id,
        status="pending_payment",
        activation_date=now,
        next_billing_date=next_billing,
        is_active=False
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    invoice = Invoice(
        user_id=current_user.id,
        subscription_id=subscription.id,
        amount=tariff.monthly_price,
        status="pending",
        billing_period_start=now,
        billing_period_end=next_billing,
        due_date=now + timedelta(days=10),
        created_at=now
    )
    
    db.add(invoice)
    db.commit()
    log_audit(
        action=AuditAction.INVOICE_CREATED,
        user_id=current_user.id,
        details=f"Prepaid activation requested for tariff {tariff.id}; invoice created",
        ip_address=client_ip,
        success=True
    )
    db.refresh(subscription)
    subscription.tariff_plan = tariff
    
    return subscription


@router.get("", response_model=List[SubscriptionResponse])
def get_user_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).all()
    for sub in subscriptions:
        sub.tariff_plan = db.query(TariffPlan).filter(TariffPlan.id == sub.tariff_id).first()
    
    return subscriptions


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подписка не найдена"
        )
    if not (current_user.id == subscription.user_id or current_user.role in ["operator", "admin"]):
        log_security_event(
            event_type="unauthorized_access_attempt",
            user_id=current_user.id,
            reason=f"Attempted access to subscription {subscription_id}",
            severity="WARNING"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен"
        )
    
    subscription.tariff_plan = db.query(TariffPlan).filter(TariffPlan.id == subscription.tariff_id).first()
    
    return subscription


@router.get("/user/{user_id}", response_model=List[SubscriptionResponse])
def get_user_subscriptions_for_operator(
    user_id: int,
    current_user: User = Depends(get_current_operator),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None)
):
    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "unknown"

    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).all()

    for sub in subscriptions:
        sub.tariff_plan = db.query(TariffPlan).filter(TariffPlan.id == sub.tariff_id).first()

    log_audit(
        action=AuditAction.SUBSCRIPTION_VIEWED,
        user_id=current_user.id,
        details=f"{current_user.role} accessed subscriptions for user {user_id}",
        ip_address=client_ip,
        success=True
    )

    return subscriptions
