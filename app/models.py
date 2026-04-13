from sqlalchemy import Column, Integer, String, DateTime, Float, Enum as SQLEnum, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class User(Base):
    """
    Модель пользователя.
    Пароль хранится только в виде хеша bcrypt.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)  # bcrypt hash
    role = Column(String(20), default="customer", nullable=False)  # customer, operator, admin
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Отношения
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


class TariffPlan(Base):
    """
    Тарифный план телекоммуникационных услуг.
    """
    __tablename__ = "tariff_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    monthly_price = Column(Float, nullable=False)  # Цена в валюте
    data_limit_gb = Column(Float, nullable=False)  # Лимит данных в ГБ
    minutes_limit = Column(Integer, nullable=False)  # Лимит минут
    sms_limit = Column(Integer, nullable=False)  # Лимит SMS
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Отношения
    subscriptions = relationship("Subscription", back_populates="tariff_plan")


class Subscription(Base):
    """
    Подписка пользователя на тарифный план.
    """
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tariff_id = Column(Integer, ForeignKey("tariff_plans.id"), nullable=False)
    status = Column(String(20), default="active", nullable=False)  # active, suspended, cancelled
    activation_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    next_billing_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Отношения
    user = relationship("User", back_populates="subscriptions")
    tariff_plan = relationship("TariffPlan", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")


class Invoice(Base):
    """
    Счет для клиента.
    Содержит расчет стоимости услуг.
    """
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending, paid, overdue
    billing_period_start = Column(DateTime, nullable=False)
    billing_period_end = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    
    # Отношения
    user = relationship("User", back_populates="invoices")
    subscription = relationship("Subscription", back_populates="invoices")


class AuditLog(Base):
    """
    Лог аудита для критичных действий.
    Не содержит чувствительных данных (пароли, токены, ПДн).
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    action_details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Отношения
    user = relationship("User", back_populates="audit_logs")
