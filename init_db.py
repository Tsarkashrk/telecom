"""
Скрипт инициализации БД с тестовыми данными.
Для работы с PostgreSQL убедитесь, что база данных создана:
  psql -U postgres -c "CREATE DATABASE telecom_db;"
"""
from app.database import SessionLocal, engine
from app.models import Base, User, TariffPlan, Subscription, Invoice
from app.security import hash_password
from datetime import datetime, timedelta, timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание таблиц
logger.info("Creating database tables...")
Base.metadata.create_all(bind=engine)
logger.info("✓ Tables created successfully")

db = SessionLocal()

try:
    # Удаление существующих данных
    db.query(Invoice).delete()
    db.query(Subscription).delete()
    db.query(User).delete()
    db.query(TariffPlan).delete()
    db.commit()
    
    # Создание тестовых пользователей
    print("Creating test users...")
    
    # Администратор
    admin = User(
        username="admin",
        email="admin@telecom.local",
        phone="+7-999-000-0001",
        hashed_password=hash_password("Admin@1234567890"),
        role="admin",
        is_active=True
    )
    db.add(admin)
    
    # Оператор
    operator = User(
        username="operator",
        email="operator@telecom.local",
        phone="+7-999-000-0002",
        hashed_password=hash_password("Operator@123456789"),
        role="operator",
        is_active=True
    )
    db.add(operator)
    
    # Тестовый клиент 1
    customer1 = User(
        username="customer1",
        email="customer1@example.com",
        phone="+7-900-100-0001",
        hashed_password=hash_password("Customer@123456789"),
        role="customer",
        is_active=True
    )
    db.add(customer1)
    
    # Тестовый клиент 2
    customer2 = User(
        username="customer2",
        email="customer2@example.com",
        phone="+7-900-100-0002",
        hashed_password=hash_password("Customer@123456789"),
        role="customer",
        is_active=True
    )
    db.add(customer2)
    
    db.commit()
    print(f"✓ Created users: admin, operator, customer1, customer2")
    
    # Создание тарифных планов
    print("Creating tariff plans...")
    
    tariff_basic = TariffPlan(
        name="Базовый",
        description="Базовый тариф для личного использования",
        monthly_price=299.99,
        data_limit_gb=10.0,
        minutes_limit=500,
        sms_limit=100,
        is_active=True
    )
    db.add(tariff_basic)
    
    tariff_standard = TariffPlan(
        name="Стандартный",
        description="Стандартный тариф со средним использованием",
        monthly_price=599.99,
        data_limit_gb=50.0,
        minutes_limit=1500,
        sms_limit=500,
        is_active=True
    )
    db.add(tariff_standard)
    
    tariff_premium = TariffPlan(
        name="Премиум",
        description="Премиум тариф с неограниченным использованием",
        monthly_price=999.99,
        data_limit_gb=200.0,
        minutes_limit=5000,
        sms_limit=2000,
        is_active=True
    )
    db.add(tariff_premium)
    
    db.commit()
    print(f"✓ Created tariff plans: Basic, Standard, Premium")
    
    # Создание подписки для customer1
    print("Creating subscriptions...")
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    next_billing = now + timedelta(days=30)
    
    subscription1 = Subscription(
        user_id=customer1.id,
        tariff_id=tariff_standard.id,
        status="active",
        activation_date=now,
        next_billing_date=next_billing,
        is_active=True
    )
    db.add(subscription1)
    
    db.commit()
    print(f"✓ Created subscription for customer1 (Standard tariff)")
    
    # Создание счетов для customer1
    print("Creating invoices...")
    
    invoice1 = Invoice(
        user_id=customer1.id,
        subscription_id=subscription1.id,
        amount=tariff_standard.monthly_price,
        status="pending",
        billing_period_start=now,
        billing_period_end=next_billing,
        due_date=now + timedelta(days=10),
        created_at=now
    )
    db.add(invoice1)
    
    # Создание старого счета
    old_now = now - timedelta(days=30)
    old_next = now
    
    invoice2 = Invoice(
        user_id=customer1.id,
        subscription_id=subscription1.id,
        amount=tariff_standard.monthly_price,
        status="paid",
        billing_period_start=old_now,
        billing_period_end=old_next,
        due_date=old_now + timedelta(days=10),
        created_at=old_now,
        paid_at=old_now + timedelta(days=5)
    )
    db.add(invoice2)
    
    db.commit()
    print(f"✓ Created invoices for customer1")
    
    print("\n✅ Database initialization completed successfully!")
    print("\nTest Credentials:")
    print("=" * 50)
    print("Admin:")
    print("  Username: admin")
    print("  Password: Admin@1234567890")
    print("-" * 50)
    print("Operator:")
    print("  Username: operator")
    print("  Password: Operator@123456789")
    print("-" * 50)
    print("Customer 1:")
    print("  Username: customer1")
    print("  Password: Customer@123456789")
    print("-" * 50)
    print("Customer 2:")
    print("  Username: customer2")
    print("  Password: Customer@123456789")
    print("=" * 50)
    
finally:
    db.close()
