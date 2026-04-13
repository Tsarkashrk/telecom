"""
Тесты для MVP системы.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.models import Base, User, TariffPlan
from app.security import hash_password

# Используем in-memory SQLite для тестов
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


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
    """Создание тестовых данных"""
    db = TestingSessionLocal()
    
    # Создание тестового пользователя
    test_user = User(
        username="testuser",
        email="test@example.com",
        phone="+7-999-000-0001",
        hashed_password=hash_password("TestPassword@123"),
        role="customer",
        is_active=True
    )
    db.add(test_user)
    
    # Создание админа
    admin_user = User(
        username="admin",
        email="admin@example.com",
        phone="+7-999-000-0002",
        hashed_password=hash_password("AdminPassword@123"),
        role="admin",
        is_active=True
    )
    db.add(admin_user)
    
    # Создание тарифного плана
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
    """Тесты аутентификации"""
    
    def test_register_user_success(self):
        """Тест успешной регистрации"""
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
        """Тест регистрации с дублирующимся username"""
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
        """Тест успешного входа"""
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
        """Тест входа с неверным пароль"""
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
        """Тест входа для несуществующего пользователя"""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "nonexistent",
                "password": "Password@123"
            }
        )
        assert response.status_code == 401
    
    def test_get_current_user(self):
        """Тест получения информации о текущем пользователе"""
        # Сначала логинимся
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "TestPassword@123"
            }
        )
        token = login_response.json()["access_token"]
        
        # Получаем информацию о пользователе
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["username"] == "testuser"
        assert "hashed_password" not in response.json()
    
    def test_get_current_user_invalid_token(self):
        """Тест получения информации с неверным токеном"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


class TestSubscriptions:
    """Тесты подписок"""
    
    def test_get_tariffs(self):
        """Тест получения списка тарифов"""
        response = client.get("/api/subscriptions/tariffs")
        assert response.status_code == 200
        assert len(response.json()) > 0
    
    def test_activate_tariff_success(self):
        """Тест активации тарифа"""
        # Логинимся
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "TestPassword@123"
            }
        )
        token = login_response.json()["access_token"]
        
        # Активируем тариф
        response = client.post(
            "/api/subscriptions/activate",
            json={"tariff_id": 1},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 201
        assert response.json()["status"] == "active"
    
    def test_get_subscriptions(self):
        """Тест получения подписок пользователя"""
        # Логинимся
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "TestPassword@123"
            }
        )
        token = login_response.json()["access_token"]
        
        # Получаем подписки
        response = client.get(
            "/api/subscriptions",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestInvoices:
    """Тесты биллинга"""
    
    def test_get_invoices(self):
        """Тест получения счетов"""
        # Логинимся
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "TestPassword@123"
            }
        )
        token = login_response.json()["access_token"]
        
        # Получаем счета
        response = client.get(
            "/api/billing/invoices",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_invoice_unauthorized(self):
        """Тест попытки доступа к счету без авторизации"""
        response = client.get("/api/billing/invoices/1")
        assert response.status_code == 401


class TestValidation:
    """Тесты валидации входных данных"""
    
    def test_register_invalid_username(self):
        """Тест регистрации с недопустимым username"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "user@name",  # @ не разрешен
                "email": "user@example.com",
                "phone": "+7-999-000-0001",
                "password": "Password@123"
            }
        )
        assert response.status_code == 422
    
    def test_register_invalid_phone(self):
        """Тест регистрации с недопустимым номером телефона"""
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
        """Тест регистрации со слабым пароль"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "user@example.com",
                "phone": "+7-999-000-0001",
                "password": "weak"  # Слишком короткий и без требуемых символов
            }
        )
        assert response.status_code == 422
    
    def test_register_short_username(self):
        """Тест регистрации с коротким username"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "ab",  # Меньше 3
                "email": "user@example.com",
                "phone": "+7-999-000-0001",
                "password": "Password@123"
            }
        )
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
