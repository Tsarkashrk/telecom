# Структура проекта MVP системы

```
telecom/
├── app/
│   ├── __init__.py
│   ├── main.py                    # Основное приложение FastAPI
│   ├── config.py                  # Конфигурация из переменных окружения
│   ├── database.py                # Подключение к PostgreSQL
│   ├── models.py                  # ORM модели (5 таблиц)
│   ├── schemas.py                 # Pydantic валидация (input/output)
│   ├── security.py                # Криптография (bcrypt, JWT)
│   ├── dependencies.py            # Аутентификация и авторизация
│   ├── logging_config.py          # Аудит логирование
│   └── routers/
│       ├── __init__.py
│       ├── auth.py                # Регистрация, вход
│       ├── subscriptions.py       # Управление подписками
│       └── invoices.py            # Биллинг и счета
│
├── tests/
│   ├── __init__.py
│   └── test_api.py                # Unit тесты
│
├── init_db.py                     # Инициализация БД с тестовыми данными
├── requirements.txt               # Зависимости (Python packages)
├── .env.example                   # Шаблон переменных окружения
├── .gitignore                     # Исключение из git
│
├── setup.sh                       # Скрипт автоматической установки
├── run.sh                         # Скрипт запуска приложения
│
├── README.md                      # Полная документация
├── QUICKSTART.md                  # Быстрый старт
├── SECURITY_ANALYSIS.md           # Полный анализ безопасности
├── DIAGRAMS.md                    # Диаграммы архитектуры
├── REQUIREMENTS_CHECKLIST.md      # Проверка выполнения требований
└── PROJECT_STRUCTURE.md           # Этот файл
```

## 📁 Описание ключевых файлов

### app/

#### main.py

- FastAPI приложение
- Подключение роутеров
- Обработчики исключений
- Lifecycle events (startup/shutdown)
- Выполняет `Base.metadata.create_all()` при старте

#### config.py

- Класс Settings (Pydantic)
- Загрузка из .env файла
- Переменные: DATABASE_URL, SECRET_KEY, ALGORITHM, TTL

#### database.py

- Подключение к PostgreSQL (SQLAlchemy engine)
- pool_pre_ping для проверки соединения
- SessionLocal (sessionmaker)
- Генератор get_db() для dependency injection

#### models.py

- 5 ORM моделей:
  - **User** - пользователи (id, username, email, phone, hashed_password, role)
  - **TariffPlan** - тарифы (name, price, limits)
  - **Subscription** - подписки (user_id, tariff_id, status, dates)
  - **Invoice** - счета (user_id, subscription_id, amount, status)
  - **AuditLog** - логирование (user_id, action, details, ip_address, timestamp)

#### schemas.py

- Pydantic валидация входных данных:
  - **UserRegisterRequest** - регистрация (username, email, phone, password с валидацией)
  - **UserLoginRequest** - вход (username, password)
  - **TokenResponse** - токены (access_token, refresh_token)
  - **ActivateTariffRequest** - активация тарифа (tariff_id > 0)
  - Другие response schemas (без пароля, без ПДн)

#### security.py

- `hash_password()` - bcrypt хеширование
- `verify_password()` - проверка пароля
- `create_access_token()` - JWT access (30 минут)
- `create_refresh_token()` - JWT refresh (7 дней)
- `verify_token()` - декодирование и валидация JWT

#### dependencies.py

- `get_current_user()` - проверка JWT токена, dependency injection
- `get_current_admin()` - проверка роли admin
- `get_current_operator()` - проверка роли operator/admin
- `verify_object_access()` - проверка ownership

#### logging_config.py

- `AuditAction` enum - типы действий
- `log_audit()` - логирование действий (без ПДн)
- `log_security_event()` - логирование событий безопасности

### app/routers/

#### auth.py

- `POST /api/auth/register` - регистрация (с валидацией)
- `POST /api/auth/login` - вход (с защитой от brute-force)
- `GET /api/auth/me` - текущий пользователь
- Защита от brute-force: 5 попыток за 15 минут
- Нейтральные сообщения об ошибках

#### subscriptions.py

- `GET /api/subscriptions/tariffs` - список тарифов
- `POST /api/subscriptions/activate` - активировать тариф
- `GET /api/subscriptions` - мои подписки
- `GET /api/subscriptions/{id}` - подписка (с проверкой доступа)
- Параметризованные запросы
- Проверка IDOR

#### invoices.py

- `GET /api/billing/invoices` - мои счета
- `GET /api/billing/invoices/{id}` - счет (с проверкой доступа)
- `GET /api/billing/invoices/{id}/status` - статус счета
- `GET /api/billing/invoices/user/{user_id}` - только admin
- Логирование всех действий
- Object-level authorization

### tests/

#### test_api.py

- Тесты регистрации, входа
- Тесты авторизации и доступа
- Тесты валидации входных данных
- Использует in-memory SQLite для тестов

## 🔐 Безопасность - ключевые компоненты

| Компонент                 | Реализация                   | Файл                          |
| ------------------------- | ---------------------------- | ----------------------------- |
| **Аутентификация**        | bcrypt + JWT HS256           | security.py, auth.py          |
| **Авторизация**           | Role-based + object-level    | dependencies.py, \*\*/routers |
| **Валидация**             | Pydantic + regex             | schemas.py                    |
| **SQL Security**          | Параметризованные запросы    | models.py, routers/\*         |
| **Криптография**          | bcrypt, HS256 (no MD5/SHA1)  | security.py                   |
| **Логирование**           | Без ПДн, без паролей/токенов | logging_config.py, routers/\* |
| **Защита от IDOR**        | Проверка ownership           | dependencies.py, routers/\*   |
| **Защита от brute-force** | Лимит попыток                | auth.py                       |
| **Безопасные ошибки**     | Нейтральные сообщения        | main.py, routers/\*           |

## 📊 Модель данных

```
┌─────────────────┐
│     users       │
├─────────────────┤
│ id (PK)         │
│ username (UK)   │
│ email (UK)      │
│ phone (UK)      │
│ hashed_password │
│ role            │
│ is_active       │
│ created_at      │
└────────┬────────┘
         │
         ├─────────────────────────────────────┐
         │                                     │
         ▼                                     ▼
┌──────────────────┐              ┌──────────────────┐
│  subscriptions   │              │  audit_logs      │
├──────────────────┤              ├──────────────────┤
│ id (PK)          │              │ id (PK)          │
│ user_id (FK)     │              │ user_id (FK)     │
│ tariff_id (FK)   │              │ action           │
│ status           │              │ ip_address       │
│ activation_date  │              │ success          │
│ next_billing_date│              │ timestamp        │
└────────┬─────────┘              └──────────────────┘
         │
         ├──────────────┐
         │              │
         ▼              ▼
┌──────────────────┐ ┌──────────────────┐
│    invoices      │ │  tariff_plans    │
├──────────────────┤ ├──────────────────┤
│ id (PK)          │ │ id (PK)          │
│ user_id (FK)     │ │ name             │
│ subscription_id  │ │ description      │
│ amount           │ │ monthly_price    │
│ status           │ │ data_limit_gb    │
│ billing_dates    │ │ minutes_limit    │
│ due_date         │ │ sms_limit        │
│ paid_at          │ │ is_active        │
└──────────────────┘ └──────────────────┘
```

## 🔄 Основной бизнес-сценарий

```
Customer Registration Flow:
1. POST /api/auth/register
   ├─ Input validation (Pydantic)
   ├─ Check uniqueness (email, username, phone)
   ├─ Hash password (bcrypt)
   └─ Create user (role=customer)

2. POST /api/auth/login
   ├─ Find user
   ├─ Verify password
   ├─ Create JWT tokens (access + refresh)
   └─ Return tokens

3. POST /api/subscriptions/activate
   ├─ Validate token (JWT verify)
   ├─ Find tariff plan
   ├─ Create subscription
   └─ Create first invoice

4. GET /api/billing/invoices/{id}
   ├─ Validate token
   ├─ Check ownership (invoice.user_id == current_user.id)
   ├─ Log audit event
   └─ Return invoice (safe fields only)
```

## 📦 Зависимости

| Пакет             | Версия  | Назначение               |
| ----------------- | ------- | ------------------------ |
| fastapi           | 0.104.1 | Web framework            |
| uvicorn           | 0.24.0  | ASGI server              |
| sqlalchemy        | 2.0.23  | ORM                      |
| psycopg2-binary   | 2.9.9   | PostgreSQL driver        |
| pydantic          | 2.4.2   | Data validation          |
| pydantic-settings | 2.0.3   | Config management        |
| passlib           | 1.7.4   | Password utilities       |
| bcrypt            | 4.1.1   | Password hashing         |
| pyjwt             | 2.8.1   | JWT tokens               |
| pytest            | 7.4.3   | Testing                  |
| bandit            | 1.7.5   | SAST (Security analysis) |
| pip-audit         | 2.6.1   | SCA (Dependency check)   |

## 🎯 Выполненные требования

✅ Структурная схема (DIAGRAMS.md)
✅ Блок-схемы (DIAGRAMS.md)
✅ Параметризованные SQL запросы (models.py, routers/\*)
✅ Валидация входных данных (schemas.py)
✅ Хеширование паролей bcrypt (security.py)
✅ JWT токены с TTL (security.py)
✅ Проверка доступа на server стороне (dependencies.py)
✅ Object-level authorization (routers/invoices.py)
✅ Безопасные сообщения об ошибках (main.py)
✅ Аудит логирование без ПДн (logging_config.py)
✅ Исключение ПДн из API (schemas.py)
✅ Современная криптография (security.py)
✅ Нет hardcoded секретов (.env)
✅ Зафиксированные версии (requirements.txt)
✅ Ready для SAST/SCA (setup.sh)

## 🚀 Быстрый старт

```bash
# Автоматическая установка
chmod +x setup.sh
./setup.sh

# Запуск
chmod +x run.sh
./run.sh

# API документация
# http://localhost:8000/docs
```

Подробнее в [QUICKSTART.md](QUICKSTART.md)
