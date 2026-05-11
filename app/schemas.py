from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import datetime
from typing import Optional, List
import re

from app.input_security import (
    normalize_phone,
    normalize_username,
    validate_username_allowlist,
)


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        return validate_username_allowlist(normalize_username(v))

    @field_validator('email')
    @classmethod
    def normalize_email(cls, v):
        return v.strip().lower()
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        return normalize_phone(v)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not re.search(r'\d', v):
            raise ValueError('Пароль должен содержать цифру')
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('Пароль должен содержать букву')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Пароль должен содержать спецсимвол')
        return v


class UserLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        return validate_username_allowlist(normalize_username(v))


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, max_length=4096)

    @field_validator('refresh_token')
    @classmethod
    def normalize_refresh_token(cls, v):
        return v.strip()


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    phone: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TariffPlanResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    monthly_price: float
    data_limit_gb: float
    minutes_limit: int
    sms_limit: int
    is_active: bool
    
    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    tariff_id: int
    tariff_plan: Optional[TariffPlanResponse] = None
    status: str
    activation_date: datetime
    next_billing_date: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    id: int
    subscription_id: int
    amount: float
    status: str
    billing_period_start: datetime
    billing_period_end: datetime
    due_date: datetime
    created_at: datetime
    paid_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ActivateTariffRequest(BaseModel):
    tariff_id: int = Field(..., gt=0)


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
