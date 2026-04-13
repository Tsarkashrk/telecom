# Телекоммуникационная платформа MVP

Минимально жизнеспособный продукт (MVP) системы регистрации клиентов и выставления счетов с соблюдением современных требований безопасности.

## 🎯 Требования

- Python 3.12+
- FastAPI
- SQLAlchemy + PostgreSQL
- Pydantic для валидации
- bcrypt для хеширования паролей
- JWT с ограниченным сроком жизни

## 📦 Установка

### 1. Клонирование и подготовка окружения

```bash
cd /Users/tsarevich/web/telecom
python3.12 -m venv venv
source venv/bin/activate
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Создание .env файла

```bash
cp .env.example .env
```

Обновите параметры в `.env`:

```
DATABASE_URL=postgresql://postgres:your_password@localhost/telecom_db
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
```

### 4. Создание БД в PostgreSQL

```bash
# Подключитесь к PostgreSQL
psql -U postgres

# Создайте базу данных
CREATE DATABASE telecom_db;

# Выход
\q
```

### 5. Инициализация таблиц и тестовых данных

```bash
python init_db.py
```

## 🚀 Запуск

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API будет доступен на `http://localhost:8000`

Документация Swagger: `http://localhost:8000/docs`

## 🔐 Тестовые учетные данные

### Администратор

- Username: `admin`
- Password: `Admin@1234567890`
- Email: `admin@telecom.local`

### Оператор

- Username: `operator`
- Password: `Operator@123456789`
- Email: `operator@telecom.local`

### Клиент 1

- Username: `customer1`
- Password: `Customer@123456789`
- Email: `customer1@example.com`

### Клиент 2

- Username: `customer2`
- Password: `Customer@123456789`
- Email: `customer2@example.com`

## 📚 API Эндпоинты

### Аутентификация

```bash
# Регистрация
POST /api/auth/register
{
  "username": "newuser",
  "email": "user@example.com",
  "phone": "+7-999-000-0001",
  "password": "Password@123"
}

# Вход
POST /api/auth/login
{
  "username": "customer1",
  "password": "Customer@123456789"
}

# Получить текущего пользователя
GET /api/auth/me
Headers: Authorization: Bearer <access_token>
```

### Подписки

```bash
# Список доступных тарифов
GET /api/subscriptions/tariffs

# Активировать тариф
POST /api/subscriptions/activate
Headers: Authorization: Bearer <access_token>
{
  "tariff_id": 1
}

# Мои подписки
GET /api/subscriptions
Headers: Authorization: Bearer <access_token>

# Информация о подписке
GET /api/subscriptions/{subscription_id}
Headers: Authorization: Bearer <access_token>
```

### Биллинг

```bash
# Мои счета
GET /api/billing/invoices
Headers: Authorization: Bearer <access_token>

# Информация о счете
GET /api/billing/invoices/{invoice_id}
Headers: Authorization: Bearer <access_token>

# Статус счета
GET /api/billing/invoices/{invoice_id}/status
Headers: Authorization: Bearer <access_token>

# Счета пользователя (только admin)
GET /api/billing/invoices/user/{user_id}
Headers: Authorization: Bearer <admin_token>
```

## 🧪 Тестирование

### Запуск тестов

```bash
pytest tests/ -v
```

### SAST анализ (Bandit)

```bash
bandit -r app/
```

### SCA анализ (pip-audit)

```bash
pip-audit
```

## 🔐 Особенности безопасности

### ✅ Аутентификация

- **Хеширование пароля:** bcrypt (автоматический salt)
- **Access Token:** JWT с TTL 30 минут
- **Refresh Token:** JWT с TTL 7 дней
- **Защита от brute-force:** 5 попыток за 15 минут

### ✅ Авторизация

- **Role-Based Access Control:** customer, operator, admin
- **Object-Level Access:** Клиент видит только свои счета
- **Серверная проверка:** Все проверки на backend

### ✅ Валидация

- **Pydantic schemas:** Типизация и валидация всех входных данных
- **Regex validation:** Username, phone number
- **Range checks:** Длина, диапазон значений

### ✅ SQL Security

- **Параметризованные запросы:** SQLAlchemy ORM защищает от инъекций
- **Foreign Keys:** Целостность данных
- **Constraints:** На уровне БД

### ✅ Logging & Auditing

- **Аудит действий:** Без логирования пароля, токенов, ПДн
- **Security events:** Попытки несанкционированного доступа
- **Безопасные сообщения:** Нейтральные ошибки, не раскрывают детали

### ✅ Data Protection

- **Исключение чувствительных данных из API:** Нет пароли, токены в responses
- **Переменные окружения:** SECRET_KEY, DATABASE_URL в .env
- **Foreign keys:** Гарантируют целостность

## 📊 Архитектура

```
┌─────────────────────────────────────────────┐
│          FastAPI Application                │
├─────────────────────────────────────────────┤
│  Routes:                                    │
│  • auth (register, login)                   │
│  • subscriptions (activate, list)           │
│  • invoices (view, list)                    │
├─────────────────────────────────────────────┤
│  Security Layer:                            │
│  • JWT validation                           │
│  • Role-based access control                │
│  • Object-level authorization               │
├─────────────────────────────────────────────┤
│  Validation Layer (Pydantic):               │
│  • Input type checking                      │
│  • Range validation                         │
│  • Format validation (regex)                │
├─────────────────────────────────────────────┤
│  Database Layer (SQLAlchemy + SQLite):      │
│  • Parameterized queries                    │
│  • ORM models                               │
│  • Foreign keys & constraints               │
└─────────────────────────────────────────────┘
```

## 📝 Модель данных

```
Users
├── id (PK)
├── username (UNIQUE)
├── email (UNIQUE)
├── phone (UNIQUE)
├── hashed_password (bcrypt)
├── role (customer|operator|admin)
├── is_active
└── created_at/updated_at

TariffPlans
├── id (PK)
├── name
├── description
├── monthly_price
├── data_limit_gb
├── minutes_limit
├── sms_limit
└── is_active

Subscriptions
├── id (PK)
├── user_id (FK → Users)
├── tariff_id (FK → TariffPlans)
├── status (active|suspended|cancelled)
├── activation_date
├── next_billing_date
└── is_active

Invoices
├── id (PK)
├── user_id (FK → Users)
├── subscription_id (FK → Subscriptions)
├── amount
├── status (pending|paid|overdue)
├── billing_period_start/end
├── due_date
├── created_at
└── paid_at

AuditLogs
├── id (PK)
├── user_id (FK → Users, nullable)
├── action
├── action_details
├── ip_address
├── success
└── timestamp
```

## 🛡️ Требования безопасности (OWASP)

| OWASP | Уязвимость                | Статус | Реализация                                 |
| ----- | ------------------------- | ------ | ------------------------------------------ |
| A01   | Broken Access Control     | ✅     | Object-level checks, role verification     |
| A02   | Cryptographic Failures    | ✅     | bcrypt + JWT HS256                         |
| A03   | Injection                 | ✅     | Parameterized queries, Pydantic validation |
| A04   | Insecure Design           | ✅     | Явные проверки авторизации                 |
| A05   | Security Misconfiguration | ✅     | .env для секретов                          |
| A06   | Vulnerable Components     | ✅     | pip-audit готов                            |
| A07   | Auth Failures             | ✅     | bcrypt + brute-force protection            |
| A08   | Data Integrity            | ✅     | Pydantic + DB constraints                  |
| A09   | Logging & Monitoring      | ✅     | Audit logs без ПДн                         |
| A10   | SSRF                      | N/A    | Нет внешних запросов                       |

## 📋 Контрольный список безопасности

- [x] Валидация всех входных данных
- [x] Хеширование пароля (bcrypt)
- [x] JWT с ограниченным сроком жизни
- [x] Проверка авторизации на serv стороне
- [x] Защита от IDOR (object-level access)
- [x] Параметризованные SQL запросы
- [x] Логирование без чувствительных данных
- [x] Безопасные сообщения об ошибках
- [x] Защита от brute-force
- [x] Зафиксированные версии зависимостей
- [x] Исключение секретов из кода

## 🔍 Аудит безопасности

Полный анализ безопасности находится в файле `SECURITY_ANALYSIS.md`, который содержит:

1. **Определение области анализа** - компоненты, API, данные
2. **Подготовка контекста** - активы, угрозы, границы доверия
3. **Алгоритм системы** - структурная схема и блок-схемы
4. **Критичные участки кода** - анализ уязвимостей
5. **Потоки данных** - source → propagation → sink → sanitization
6. **Защитные механизмы** - проверка каждого контроля
7. **Фиксация находок** - таблица уязвимостей и их исправления
8. **Рекомендации** - меры по безопасности

## 📝 Лицензия

MIT

## ✉️ Контакты

Автор: Практическая работа №3 - Анализ безопасности MVP
Дата: Апрель 2026
