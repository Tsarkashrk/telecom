import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app import database as database_module
from app import logging_config as logging_config_module
from app.main import app
from app.database import get_db
from app.models import Base, Invoice, Subscription, TariffPlan, User
from app.security import hash_password

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)
database_module.SessionLocal = TestingSessionLocal
logging_config_module.database.SessionLocal = TestingSessionLocal


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def login_and_get_tokens(username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password}
    )
    assert response.status_code == 200
    return response.json()


def get_resource_ids() -> dict[str, int]:
    db = TestingSessionLocal()
    try:
        victim = db.query(User).filter(User.username == "victim").first()
        victim_subscription = (
            db.query(Subscription)
            .filter(Subscription.user_id == victim.id)
            .order_by(Subscription.id)
            .first()
        )
        victim_invoice = (
            db.query(Invoice)
            .filter(Invoice.user_id == victim.id)
            .order_by(Invoice.id)
            .first()
        )
        return {
            "victim_user_id": victim.id,
            "victim_subscription_id": victim_subscription.id,
            "victim_invoice_id": victim_invoice.id,
        }
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_test_data():
    db = TestingSessionLocal()
    
    test_user = User(
        username="testuser",
        email="test@example.com",
        phone="+7-999-000-0001",
        hashed_password=hash_password("TestPassword@123"),
        role="customer",
        is_active=True
    )
    db.add(test_user)
    
    admin_user = User(
        username="admin",
        email="admin@example.com",
        phone="+7-999-000-0002",
        hashed_password=hash_password("AdminPassword@123"),
        role="admin",
        is_active=True
    )
    db.add(admin_user)

    operator_user = User(
        username="operator1",
        email="operator@example.com",
        phone="+7-999-000-0003",
        hashed_password=hash_password("OperatorPassword@123"),
        role="operator",
        is_active=True
    )
    db.add(operator_user)

    outsider_user = User(
        username="outsider",
        email="outsider@example.com",
        phone="+7-999-000-0004",
        hashed_password=hash_password("OutsiderPassword@123"),
        role="customer",
        is_active=True
    )
    db.add(outsider_user)

    victim_user = User(
        username="victim",
        email="victim@example.com",
        phone="+7-999-000-0005",
        hashed_password=hash_password("VictimPassword@123"),
        role="customer",
        is_active=True
    )
    db.add(victim_user)
    
    tariff = TariffPlan(
        name="Test Tariff",
        monthly_price=99.99,
        data_limit_gb=10.0,
        minutes_limit=100,
        sms_limit=50,
        is_active=True
    )
    db.add(tariff)
    
    db.commit()

    now = datetime.utcnow()
    victim_subscription = Subscription(
        user_id=victim_user.id,
        tariff_id=tariff.id,
        status="active",
        activation_date=now - timedelta(days=5),
        next_billing_date=now + timedelta(days=25),
        is_active=True
    )
    db.add(victim_subscription)
    db.commit()

    victim_invoice = Invoice(
        user_id=victim_user.id,
        subscription_id=victim_subscription.id,
        amount=99.99,
        status="pending",
        billing_period_start=now - timedelta(days=5),
        billing_period_end=now + timedelta(days=25),
        due_date=now + timedelta(days=5),
        created_at=now - timedelta(days=5)
    )
    db.add(victim_invoice)
    db.commit()
    db.close()
    
    yield


class TestAuth:
    
    def test_register_user_success(self):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "NEWUSER@example.com",
                "phone": "+7 (999) 100-0001",
                "password": "NewPassword@123"
            }
        )
        assert response.status_code == 201
        assert response.json()["username"] == "newuser"
        assert response.json()["email"] == "newuser@example.com"
        assert response.json()["phone"] == "+79991000001"
    
    def test_register_duplicate_username(self):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "another@example.com",
                "phone": "+7-999-100-0002",
                "password": "NewPassword@123"
            }
        )
        assert response.status_code == 400
    
    def test_login_success(self):
        response = client.post(
            "/api/auth/login",
            json={
                "username": " testuser ",
                "password": "TestPassword@123"
            }
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()

    def test_login_writes_audit_record_to_file(self, tmp_path):
        log_path = tmp_path / "audit.log"
        logging_config_module.configure_audit_logging(str(log_path))

        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "TestPassword@123"
            }
        )

        assert response.status_code == 200
        assert log_path.exists()

        log_contents = log_path.read_text(encoding="utf-8")
        assert "[AUDIT] Action: user_login" in log_contents
        assert "User ID:" in log_contents
        assert "Success: True" in log_contents
    
    def test_login_invalid_password(self):
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "WrongPassword@123"
            }
        )
        assert response.status_code == 401
        assert "Неверное имя пользователя или пароль" in response.json()["error"]
    
    def test_login_nonexistent_user(self):
        response = client.post(
            "/api/auth/login",
            json={
                "username": "nonexistent",
                "password": "Password@123"
            }
        )
        assert response.status_code == 401
    
    def test_get_current_user(self):
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "TestPassword@123"
            }
        )
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["username"] == "testuser"
        assert "hashed_password" not in response.json()
    
    def test_get_current_user_invalid_token(self):
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    def test_refresh_token_cannot_access_protected_endpoints(self):
        tokens = login_and_get_tokens("testuser", "TestPassword@123")

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
        )
        assert response.status_code == 401

    def test_refresh_token_rotation_rejects_old_token(self):
        tokens = login_and_get_tokens("testuser", "TestPassword@123")

        first_refresh = client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]}
        )
        assert first_refresh.status_code == 200

        reused_old_refresh = client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]}
        )
        assert reused_old_refresh.status_code == 401


class TestSubscriptions:
    
    def test_get_tariffs(self):
        response = client.get("/api/subscriptions/tariffs")
        assert response.status_code == 200
        assert len(response.json()) > 0
    
    def test_activate_tariff_success(self):
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "TestPassword@123"
            }
        )
        token = login_response.json()["access_token"]
        
        response = client.post(
            "/api/subscriptions/activate",
            json={"tariff_id": 1},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 201
        assert response.json()["status"] == "pending_payment"
    
    def test_get_subscriptions(self):
        token = login_and_get_tokens("testuser", "TestPassword@123")["access_token"]
        
        response = client.get(
            "/api/subscriptions",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_operator_can_access_other_user_subscription(self):
        token = login_and_get_tokens("operator1", "OperatorPassword@123")["access_token"]
        resource_ids = get_resource_ids()

        response = client.get(
            f"/api/subscriptions/{resource_ids['victim_subscription_id']}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["user_id"] == resource_ids["victim_user_id"]

    def test_customer_cannot_access_other_user_subscription(self):
        token = login_and_get_tokens("outsider", "OutsiderPassword@123")["access_token"]
        resource_ids = get_resource_ids()

        response = client.get(
            f"/api/subscriptions/{resource_ids['victim_subscription_id']}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


class TestInvoices:
    
    def test_get_invoices(self):
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "TestPassword@123"
            }
        )
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/api/billing/invoices",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_export_invoices_csv(self):
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "TestPassword@123"
            }
        )
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/billing/invoices/export?format=csv&limit=10&offset=0",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/csv")
        assert "Content-Disposition" in response.headers
        assert "id,subscription_id,amount" in response.text

    def test_export_invoices_json(self):
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "TestPassword@123"
            }
        )
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/billing/invoices/export?format=json&limit=10&offset=0",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("application/json")
        assert isinstance(response.json(), list)
    
    def test_get_invoice_unauthorized(self):
        response = client.get("/api/billing/invoices/1")
        assert response.status_code == 401

    def test_customer_cannot_view_other_user_invoice_status(self):
        token = login_and_get_tokens("outsider", "OutsiderPassword@123")["access_token"]
        resource_ids = get_resource_ids()

        response = client.get(
            f"/api/billing/invoices/{resource_ids['victim_invoice_id']}/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


class TestValidation:
    
    def test_register_invalid_username(self):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "user@name",
                "email": "user@example.com",
                "phone": "+7-999-000-0001",
                "password": "Password@123"
            }
        )
        assert response.status_code == 422
    
    def test_register_invalid_phone(self):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "user@example.com",
                "phone": "invalid_phone",
                "password": "Password@123"
            }
        )
        assert response.status_code == 422
    
    def test_register_weak_password(self):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "user@example.com",
                "phone": "+7-999-000-0001",
                "password": "weak" 
            }
        )
        assert response.status_code == 422
    
    def test_register_short_username(self):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "ab", 
                "email": "user@example.com",
                "phone": "+7-999-000-0001",
                "password": "Password@123"
            }
        )
        assert response.status_code == 422

    def test_reject_oversized_request_body(self):
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "A" * 70000
            }
        )
        assert response.status_code == 413
        assert response.json()["error"] == "Размер запроса превышает допустимый предел"


class TestResourceControls:

    def test_get_invoices_rejects_excessive_limit(self):
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "TestPassword@123"
            }
        )
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/billing/invoices?limit=1000",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 422

    def test_get_subscriptions_accepts_bounded_limit(self):
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "TestPassword@123"
            }
        )
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/subscriptions?limit=1&offset=0",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestSecureInputHandling:

    def test_invalid_forwarded_for_header_is_sanitized(self):
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "TestPassword@123"
            },
            headers={"X-Forwarded-For": "bad-ip\r\nforged"}
        )
        assert login_response.status_code == 200

    def test_login_rejects_invalid_username_symbols(self):
        response = client.post(
            "/api/auth/login",
            json={
                "username": "bad user!",
                "password": "Password@123"
            }
        )
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
