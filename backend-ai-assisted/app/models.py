from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, Float, ForeignKey, Boolean, Text, text
from datetime import datetime
from typing import List, Optional
from app.db_security import PLACEHOLDER_HASH


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    legacy_password_marker: Mapped[str] = mapped_column(
        "hashed_password",
        String(255),
        default=PLACEHOLDER_HASH,
        server_default=text(f"'{PLACEHOLDER_HASH}'"),
    )
    role: Mapped[str] = mapped_column(String(20), default="customer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    refresh_token_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    subscriptions: Mapped[List["Subscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    invoices: Mapped[List["Invoice"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    credentials: Mapped[Optional["UserCredential"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )


class UserCredential(Base):
    __tablename__ = "user_credentials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    password_updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="credentials")


class TariffPlan(Base):
    __tablename__ = "tariff_plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    monthly_price: Mapped[float] = mapped_column(Float)
    data_limit_gb: Mapped[float] = mapped_column(Float)
    minutes_limit: Mapped[int] = mapped_column(Integer)
    sms_limit: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    subscriptions: Mapped[List["Subscription"]] = relationship(
        back_populates="tariff_plan"
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariff_plans.id"))
    status: Mapped[str] = mapped_column(String(20), default="active")
    activation_date: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    next_billing_date: Mapped[datetime]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    tariff_plan: Mapped["TariffPlan"] = relationship(back_populates="subscriptions")
    invoices: Mapped[List["Invoice"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan"
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"))
    amount: Mapped[float]
    status: Mapped[str] = mapped_column(String(20), default="pending")
    billing_period_start: Mapped[datetime]
    billing_period_end: Mapped[datetime]
    due_date: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    paid_at: Mapped[Optional[datetime]]

    user: Mapped["User"] = relationship(back_populates="invoices")
    subscription: Mapped["Subscription"] = relationship(back_populates="invoices")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    action_details: Mapped[Optional[str]] = mapped_column(Text)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")
