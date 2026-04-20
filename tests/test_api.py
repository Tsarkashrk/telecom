import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app import database as database_module
from app import logging_config as logging_config_module
from app.main import app
from app.database import get_db
from app.models import Base, User, TariffPlan
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
    db.close()
    
    yield


class TestAuth:
    
    def test_register_user_success(self):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "phone": "+7-999-100-0001",
                "password": "NewPassword@123"
            }
        )
        assert response.status_code == 201
        assert response.json()["username"] == "newuser"
    
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
                "username": "testuser",
                "password": "TestPassword@123"
            }
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()
    
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
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "TestPassword@123"
            }
        )
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/api/subscriptions",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


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
    
    def test_get_invoice_unauthorized(self):
        response = client.get("/api/billing/invoices/1")
        assert response.status_code == 401


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
