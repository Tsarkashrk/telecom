from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timezone
from typing import List, Optional

from app.database import get_db
from app.models import User, Invoice, Subscription
from app.schemas import InvoiceResponse, ErrorResponse
from app.dependencies import get_current_user, get_current_operator
from app.logging_config import log_audit, log_security_event, AuditAction

router = APIRouter()


@router.get("/invoices", response_model=List[InvoiceResponse])
def get_user_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить все счета текущего пользователя.
    
    Требования безопасности:
    - Проверка прав доступа: клиент видит только свои счета
    - Не возвращаем лишние поля (в том числе email, phone и другие ПДн)
    - Параметризованный запрос
    """
    invoices = db.query(Invoice).filter(
        Invoice.user_id == current_user.id
    ).all()
    
    log_audit(
        action=AuditAction.INVOICE_VIEWED,
        user_id=current_user.id,
        details=f"Retrieved {len(invoices)} invoices",
        success=True
    )
    
    return invoices


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None)
):
    """
    Получить счет по ID.
    
    Требования безопасности:
    - Проверка доступа к конкретному объекту (invoice_id)
    - Клиент может видеть только свои счета
    - Администратор и оператор могут видеть счета клиентов
    - Не возвращаем ПДн клиента в ответе
    """
    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "unknown"
    
    # Параметризованный запрос
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Счет не найден"
        )
    
    # Проверка прав доступа: client видит только свой счет
    if invoice.user_id != current_user.id and current_user.role not in ["operator", "admin"]:
        log_security_event(
            event_type="unauthorized_invoice_access",
            user_id=current_user.id,
            reason=f"Attempted to access invoice {invoice_id} of user {invoice.user_id}",
            severity="WARNING"
        )
        # Логирование попытки несанкционированного доступа
        log_audit(
            action=AuditAction.UNAUTHORIZED_ACCESS_ATTEMPT,
            user_id=current_user.id,
            details=f"Invoice ID: {invoice_id}",
            ip_address=client_ip,
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен"
        )
    
    # Логирование успешного просмотра счета
    log_audit(
        action=AuditAction.INVOICE_VIEWED,
        user_id=current_user.id,
        details=f"Invoice ID: {invoice_id}, Amount: {invoice.amount}",
        success=True
    )
    
    return invoice


@router.get("/invoices/{invoice_id}/status", response_model=dict)
def get_invoice_status(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить статус счета.
    Упрощенный эндпоинт для проверки статуса платежа.
    """
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Счет не найден"
        )
    
    # Проверка доступа
    if invoice.user_id != current_user.id and current_user.role not in ["operator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен"
        )
    
    return {
        "invoice_id": invoice.id,
        "status": invoice.status,
        "amount": invoice.amount,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None
    }


@router.get("/invoices/user/{user_id}", response_model=List[InvoiceResponse])
def get_user_invoices_admin(
    user_id: int,
    current_user: User = Depends(get_current_operator),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None)
):
    """
    Получить счета пользователя (операторский/администраторский API).
    
    Требования безопасности:
    - Только операторы и администраторы могут использовать этот эндпоинт
    - Логирование доступа
    - Параметризованный запрос
    """
    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "unknown"
    
    # Параметризованный запрос
    invoices = db.query(Invoice).filter(
        Invoice.user_id == user_id
    ).all()
    
    log_audit(
        action=AuditAction.INVOICE_VIEWED,
        user_id=current_user.id,
        details=f"{current_user.role} accessed invoices for user {user_id}",
        ip_address=client_ip,
        success=True
    )
    
    return invoices
