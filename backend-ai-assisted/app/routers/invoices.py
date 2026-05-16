from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import csv
import io

from app.database import get_db
from app.models import User, Invoice, Subscription
from app.schemas import InvoiceResponse, ErrorResponse
from app.config import settings
from app.dependencies import (
    ensure_invoice_access,
    get_current_operator,
    get_current_user,
)
from app.input_security import (
    extract_client_ip,
    csv_sanitize_cell,
    safe_join,
    validate_safe_filename,
)
from app.logging_config import log_audit, AuditAction

router = APIRouter()


@router.get("/invoices", response_model=List[InvoiceResponse])
def get_user_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    offset: int = Query(0, ge=0),
):

    invoices = (
        db.query(Invoice)
        .filter(Invoice.user_id == current_user.id)
        .order_by(Invoice.id)
        .limit(limit)
        .offset(offset)
        .all()
    )
    
    log_audit(
        action=AuditAction.INVOICE_VIEWED,
        user_id=current_user.id,
        details=f"Retrieved {len(invoices)} invoices",
        success=True
    )
    
    return invoices


@router.get("/invoices/export")
def export_user_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    format: str = Query("csv", min_length=3, max_length=10),
    store: bool = Query(False),
    filename: Optional[str] = Query(None, min_length=1, max_length=128),
    limit: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    offset: int = Query(0, ge=0),
):
    fmt = format.strip().lower()
    if fmt not in {"csv", "json"}:
        raise HTTPException(status_code=400, detail="Неподдерживаемый формат экспорта")

    invoices = (
        db.query(Invoice)
        .filter(Invoice.user_id == current_user.id)
        .order_by(Invoice.id)
        .limit(limit)
        .offset(offset)
        .all()
    )

    exported_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if filename is None:
        safe_name = f"invoices_user_{current_user.id}_{exported_at}.{fmt}"
    else:
        safe_name = validate_safe_filename(filename)
        if not safe_name.lower().endswith(f".{fmt}"):
            safe_name = f"{safe_name}.{fmt}"

    if fmt == "json":
        payload = [
            {
                "id": inv.id,
                "subscription_id": inv.subscription_id,
                "amount": inv.amount,
                "status": inv.status,
                "billing_period_start": inv.billing_period_start.isoformat()
                if inv.billing_period_start
                else None,
                "billing_period_end": inv.billing_period_end.isoformat()
                if inv.billing_period_end
                else None,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
            }
            for inv in invoices
        ]
        data = JSONResponse(content=payload).body or b"[]"

        if store:
            export_path = safe_join(settings.export_dir, safe_name)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            export_path.write_bytes(data)

        log_audit(
            action=AuditAction.INVOICE_VIEWED,
            user_id=current_user.id,
            details=f"Exported invoices: format={fmt}, count={len(invoices)}, store={store}",
            success=True,
        )
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
        )

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        [
            "id",
            "subscription_id",
            "amount",
            "status",
            "billing_period_start",
            "billing_period_end",
            "due_date",
            "created_at",
            "paid_at",
        ]
    )
    for inv in invoices:
        writer.writerow(
            [
                csv_sanitize_cell(inv.id),
                csv_sanitize_cell(inv.subscription_id),
                csv_sanitize_cell(inv.amount),
                csv_sanitize_cell(inv.status),
                csv_sanitize_cell(inv.billing_period_start),
                csv_sanitize_cell(inv.billing_period_end),
                csv_sanitize_cell(inv.due_date),
                csv_sanitize_cell(inv.created_at),
                csv_sanitize_cell(inv.paid_at),
            ]
        )

    csv_bytes = output.getvalue().encode("utf-8")
    if store:
        export_path = safe_join(settings.export_dir, safe_name)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_bytes(csv_bytes)

    log_audit(
        action=AuditAction.INVOICE_VIEWED,
        user_id=current_user.id,
        details=f"Exported invoices: format={fmt}, count={len(invoices)}, store={store}",
        success=True,
    )

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None)
):
    client_ip = extract_client_ip(x_forwarded_for)
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Счет не найден"
        )
    ensure_invoice_access(invoice, current_user, client_ip=client_ip)
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
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None)
):
    client_ip = extract_client_ip(x_forwarded_for)
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Счет не найден"
        )
    ensure_invoice_access(invoice, current_user, client_ip=client_ip)
    
    return {
        "invoice_id": invoice.id,
        "status": invoice.status,
        "amount": invoice.amount,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None
    }


@router.post("/invoices/{invoice_id}/pay", response_model=InvoiceResponse)
def pay_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None)
):
    client_ip = extract_client_ip(x_forwarded_for)

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Счет не найден"
        )

    ensure_invoice_access(invoice, current_user, action="pay", client_ip=client_ip)

    if invoice.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Счет уже оплачен"
        )

    if invoice.status == "overdue":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Просроченный счет нельзя оплатить через этот endpoint"
        )

    subscription = db.query(Subscription).filter(
        Subscription.id == invoice.subscription_id
    ).first()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подписка для счета не найдена"
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    invoice.status = "paid"
    invoice.paid_at = now

    subscription.status = "active"
    subscription.is_active = True
    subscription.activation_date = now
    subscription.next_billing_date = now + timedelta(days=30)

    db.commit()
    db.refresh(invoice)

    log_audit(
        action=AuditAction.INVOICE_PAID,
        user_id=current_user.id,
        details=f"Invoice {invoice.id} paid; subscription {subscription.id} activated",
        ip_address=client_ip,
        success=True
    )
    log_audit(
        action=AuditAction.TARIFF_ACTIVATED,
        user_id=subscription.user_id,
        details=f"Subscription {subscription.id} activated after prepaid invoice payment",
        ip_address=client_ip,
        success=True
    )

    return invoice


@router.get("/invoices/user/{user_id}", response_model=List[InvoiceResponse])
def get_user_invoices_admin(
    user_id: int,
    current_user: User = Depends(get_current_operator),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None),
    limit: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    offset: int = Query(0, ge=0),
):
    client_ip = extract_client_ip(x_forwarded_for)
    invoices = (
        db.query(Invoice)
        .filter(Invoice.user_id == user_id)
        .order_by(Invoice.id)
        .limit(limit)
        .offset(offset)
        .all()
    )
    
    log_audit(
        action=AuditAction.INVOICE_VIEWED,
        user_id=current_user.id,
        details=f"{current_user.role} accessed invoices for user {user_id}",
        ip_address=client_ip,
        success=True
    )
    
    return invoices
