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
from app.dependencies import get_current_user, verify_object_access
from app.logging_config import log_audit, log_security_event, AuditAction

router = APIRouter()


@router.get("/tariffs", response_model=List[TariffPlanResponse])
def get_available_tariffs(db: Session = Depends(get_db)):
    """
    Получить список доступных тарифных планов.
    Доступно всем аутентифицированным пользователям.
    """
    tariffs = db.query(TariffPlan).filter(TariffPlan.is_active == True).all()
    return tariffs


@router.post("/subscriptions/activate", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def activate_tariff(
    request: ActivateTariffRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None)
):
    """
    Активировать тариф для текущего пользователя.
    
    Требования безопасности:
    - Проверка прав доступа: пользователь может активировать тариф только для себя
    - Валидация tariff_id через Pydantic
    - Проверка существования тарифа
    - Параметризованный запрос
    """
    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "unknown"
    
    # Валидация tariff_id была выполнена Pydantic (gt=0)
    
    # Проверка существования тарифа (параметризованный запрос)
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
    
    # Проверка, есть ли уже активная подписка
    existing_subscription = db.query(Subscription).filter(
        and_(
            Subscription.user_id == current_user.id,
            Subscription.is_active == True
        )
    ).first()
    
    if existing_subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь уже имеет активную подписку"
        )
    
    # Создание подписки
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    next_billing = now + timedelta(days=30)
    
    subscription = Subscription(
        user_id=current_user.id,
        tariff_id=tariff.id,
        status="active",
        activation_date=now,
        next_billing_date=next_billing,
        is_active=True
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    # Создание первого счета
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
    
    # Логирование
    log_audit(
        action=AuditAction.TARIFF_ACTIVATED,
        user_id=current_user.id,
        details=f"Tariff ID: {tariff.id}, Plan: {tariff.name}",
        ip_address=client_ip,
        success=True
    )
    
    # Загрузка связанного тарифа
    db.refresh(subscription)
    subscription.tariff_plan = tariff
    
    return subscription


@router.get("/subscriptions", response_model=List[SubscriptionResponse])
def get_user_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить подписки текущего пользователя.
    Проверка прав доступа: пользователь видит только свои подписки.
    """
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).all()
    
    # Загрузка связанных тарифов
    for sub in subscriptions:
        sub.tariff_plan = db.query(TariffPlan).filter(TariffPlan.id == sub.tariff_id).first()
    
    return subscriptions


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить информацию о конкретной подписке.
    Проверка доступа к конкретному объекту.
    """
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подписка не найдена"
        )
    
    # Проверка прав доступа
    if not (current_user.id == subscription.user_id or current_user.role == "admin"):
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
