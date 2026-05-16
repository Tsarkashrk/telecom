from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.database import get_db
from app.config import settings
from app.input_security import extract_client_ip
from app.models import User, Subscription, TariffPlan, Invoice
from app.schemas import (
    SubscriptionResponse, ActivateTariffRequest,
    TariffPlanResponse, InvoiceResponse, ErrorResponse
)
from app.dependencies import (
    ensure_subscription_access,
    get_current_operator,
    get_current_user,
)
from app.logging_config import log_audit, log_security_event, AuditAction

router = APIRouter()


@router.get("/tariffs", response_model=List[TariffPlanResponse])
def get_available_tariffs(db: Session = Depends(get_db)):
    tariffs = (
        db.query(TariffPlan)
        .filter(TariffPlan.is_active == True)
        .order_by(TariffPlan.id)
        .limit(settings.max_page_size)
        .all()
    )
    return tariffs


@router.post("/activate", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def activate_tariff(
    request: ActivateTariffRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None)
):
    client_ip = extract_client_ip(x_forwarded_for)
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
    db: Session = Depends(get_db),
    limit: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    offset: int = Query(0, ge=0),
):
    subscriptions = (
        db.query(Subscription)
        .filter(Subscription.user_id == current_user.id)
        .order_by(Subscription.id)
        .limit(limit)
        .offset(offset)
        .all()
    )
    for sub in subscriptions:
        tariff: TariffPlan | None = db.get(TariffPlan, sub.tariff_id)

        if tariff is None:
            raise HTTPException(status_code=404, detail="Tariff not found")

        sub.tariff_plan = tariff
    
    return subscriptions


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None),
):
    client_ip = extract_client_ip(x_forwarded_for)
    subscription: Subscription | None = (
        db.query(Subscription)
        .filter(Subscription.id == subscription_id)
        .first()
    )

    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подписка не найдена",
        )

    ensure_subscription_access(subscription, current_user, client_ip)

    tariff: TariffPlan | None = db.get(TariffPlan, subscription.tariff_id)

    if tariff is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тариф не найден",
        )

    subscription.tariff_plan = tariff

    return subscription


@router.get("/user/{user_id}", response_model=List[SubscriptionResponse])
def get_user_subscriptions_for_operator(
    user_id: int,
    current_user: User = Depends(get_current_operator),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None),
    limit: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    offset: int = Query(0, ge=0),
):
    client_ip = extract_client_ip(x_forwarded_for)

    subscriptions = (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .order_by(Subscription.id)
        .limit(limit)
        .offset(offset)
        .all()
    )

    for sub in subscriptions:
        tariff: TariffPlan | None = db.get(TariffPlan, sub.tariff_id)
        if tariff is None:
            raise HTTPException(status_code=404, detail="Tariff not found")

        sub.tariff_plan = tariff

    log_audit(
        action=AuditAction.SUBSCRIPTION_VIEWED,
        user_id=current_user.id,
        details=f"{current_user.role} accessed subscriptions for user {user_id}",
        ip_address=client_ip,
        success=True
    )

    return subscriptions
