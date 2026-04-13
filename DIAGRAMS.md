# Блок-схемы и диаграммы MVP системы

## 1. Архитектурная диаграмма компонентов

```
┌────────────────────────────────────────────────────────────────────┐
│                        Client (Web/Mobile)                         │
└────────────────────┬─────────────────────────────────────────────────┘
                     │ HTTP/HTTPS
                     │
┌────────────────────▼─────────────────────────────────────────────────┐
│                    FastAPI Web Server                                 │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                  API Routes                                      │ │
│  │  ┌─────────────┐  ┌────────────────┐  ┌──────────────────────┐  │ │
│  │  │ Auth Router │  │ Subscription   │  │ Invoices Router      │  │ │
│  │  │             │  │ Router         │  │                      │  │ │
│  │  │ • register  │  │ • tariffs      │  │ • list invoices      │  │ │
│  │  │ • login     │  │ • activate     │  │ • get invoice        │  │ │
│  │  │ • me        │  │ • get_subs     │  │ • get status         │  │ │
│  │  │ • refresh   │  │ • get_sub      │  │ • admin api          │  │ │
│  │  └─────────────┘  └────────────────┘  └──────────────────────┘  │ │
│  └────────────────────┬───────────────────────────────────────────────┘ │
│                       │                                                  │
│  ┌────────────────────▼────────────────────────────────────────────────┐ │
│  │            Dependency Injection & Security Layer                    │ │
│  │  ┌───────────────────────────────────────────────────────────────┐  │ │
│  │  │ get_current_user: Verify JWT + Get User from DB              │  │ │
│  │  │ get_current_admin: Check role == "admin"                     │  │ │
│  │  │ get_current_operator: Check role in ["operator", "admin"]    │  │ │
│  │  │ verify_object_access: Check ownership (user_id)              │  │ │
│  │  └───────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────┬───────────────────────────────────────────────────┘ │
│                       │                                                    │
│  ┌────────────────────▼─────────────────────────────────────────────────┐ │
│  │           Input Validation Layer (Pydantic)                         │ │
│  │  ┌──────────────────────────────────────────────────────────────┐  │ │
│  │  │ Schemas:                                                     │  │ │
│  │  │ • UserRegisterRequest: regex, length, complexity checks     │  │ │
│  │  │ • UserLoginRequest: username, password                      │  │ │
│  │  │ • ActivateTariffRequest: gt=0 validation                    │  │ │
│  │  │ • InvoiceResponse: only public fields                       │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────┬───────────────────────────────────────────────────┘ │
│                       │                                                    │
│  ┌────────────────────▼─────────────────────────────────────────────────┐ │
│  │         Security & Crypto Layer                                     │ │
│  │  ┌──────────────────────────────────────────────────────────────┐  │ │
│  │  │ security.py:                                                 │  │ │
│  │  │ • hash_password: bcrypt hashing                              │  │ │
│  │  │ • verify_password: check against hash                        │  │ │
│  │  │ • create_access_token: JWT HS256 (30 min exp)               │  │ │
│  │  │ • create_refresh_token: JWT HS256 (7 days exp)              │  │ │
│  │  │ • verify_token: decode and validate JWT                     │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────┬───────────────────────────────────────────────────┘ │
│                       │                                                    │
│  ┌────────────────────▼─────────────────────────────────────────────────┐ │
│  │        Database Layer (SQLAlchemy ORM + SQLite)                     │ │
│  │  ┌──────────────────────────────────────────────────────────────┐  │ │
│  │  │ Models:                                                      │  │ │
│  │  │ • User: username, email, phone, hashed_password, role       │  │ │
│  │  │ • TariffPlan: name, price, data_limit, minutes, sms        │  │ │
│  │  │ • Subscription: user_id, tariff_id, status                 │  │ │
│  │  │ • Invoice: user_id, subscription_id, amount, status        │  │ │
│  │  │ • AuditLog: user_id, action, ip_address, timestamp         │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────┬───────────────────────────────────────────────────┘ │
│                       │                                                    │
│  ┌────────────────────▼─────────────────────────────────────────────────┐ │
│  │        Logging & Auditing                                           │ │
│  │  ┌──────────────────────────────────────────────────────────────┐  │ │
│  │  │ logging_config.py:                                           │  │ │
│  │  │ • log_audit: action, user_id, ip_address, success           │  │ │
│  │  │ • log_security_event: event_type, severity                  │  │ │
│  │  │ • NO passwords, tokens, PII in logs                         │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────┬───────────────────────────────────────────────────┘ │
└─────────────────────┼──────────────────────────────────────────────────────┘
                      │ SQL queries (parameterized)
                      │
         ┌────────────▼──────────────┐
         │   SQLite Database         │
         │  telecom.db               │
         │                           │
         │ Tables:                   │
         │ • users                   │
         │ • tariff_plans            │
         │ • subscriptions           │
         │ • invoices                │
         │ • audit_logs              │
         │                           │
         │ Foreign Keys:             │
         │ • subscriptions → users   │
         │ • subscriptions → plans   │
         │ • invoices → users        │
         │ • invoices → subscriptions│
         │ • audit_logs → users      │
         └───────────────────────────┘
```

## 2. Диаграмма потоков данных (DFD)

### Уровень 0 - Контекстная диаграмма

```
            ┌─────────────────────────────────┐
            │  Telecom MVP System             │
            │                                 │
            │  ┌─────────────────────────┐    │
            │  │  Authentication         │    │
            │  │  • Registration         │    │
            │  │  • Login                │    │
            │  │  • JWT Tokens           │    │
            │  └─────────────────────────┘    │
            │                                 │
            │  ┌─────────────────────────┐    │
            │  │  Subscriptions          │    │
            │  │  • View Tariffs         │    │
            │  │  • Activate Tariff      │    │
            │  │  • View Subscriptions   │    │
            │  └─────────────────────────┘    │
            │                                 │
            │  ┌─────────────────────────┐    │
            │  │  Billing                │    │
            │  │  • View Invoices        │    │
            │  │  • Check Invoice Status │    │
            │  └─────────────────────────┘    │
            │                                 │
            └────────┬────────────┬────────────┘
                     │            │
         ┌───────────▼──┐    ┌────▼──────────┐
         │   Customers  │    │   Database    │
         │   Operators  │    │   (SQLite)    │
         │   Admins     │    │               │
         └──────────────┘    └───────────────┘
```

### Уровень 1 - Основные процессы

```
External Entity:      Process:                External Entity:

                    ┌─────────────────────────┐
                    │   0. Main API Gateway   │
                    │   (FastAPI Router)      │
                    └────────┬────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
     ┌──────────┐      ┌──────────┐      ┌──────────────┐
     │   1.0    │      │   2.0    │      │    3.0       │
     │ Auth     │      │ Subscr.  │      │ Billing      │
     │ (login/  │      │ (tariff  │      │ (invoices)   │
     │ register)│      │ mgmt)    │      │              │
     └─────┬────┘      └────┬─────┘      └────┬─────────┘
           │                │                 │
           │                │                 │
           └────────┬───────┴─────────┬───────┘
                    │                 │
                    ▼                 ▼
            ┌───────────────┐  ┌──────────────┐
            │ 4.0           │  │ 5.0          │
            │ Database      │  │ Audit Logs   │
            │ (SQLAlchemy)  │  │ (Logging)    │
            └───────────────┘  └──────────────┘
```

## 3. Диаграмма аутентификации и авторизации

```
┌──────────────────────────────────────────────────────────────────┐
│                   API Request with Bearer Token                  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │ Extract token from Authorization   │
        │ Header: Bearer <JWT>               │
        └────────────────┬───────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │ verify_token()                     │
        │ - Decode JWT with SECRET_KEY       │
        │ - Check signature                  │
        │ - Check exp (expiration time)      │
        └────────┬──────────────────┬────────┘
            VALID │                │ INVALID
                  ▼                ▼
         ┌────────────────┐   ┌──────────────┐
         │ Extract user_id│   │ Return 401   │
         │ from payload   │   │ Unauthorized │
         │ (sub field)    │   └──────────────┘
         └────────┬───────┘
                  │
                  ▼
        ┌────────────────────────────────────┐
        │ Query database for User            │
        │ WHERE user.id = payload['sub']     │
        │ (Parameterized query!)             │
        └────────┬──────────────┬────────────┘
            FOUND │              │ NOT FOUND
                  ▼              ▼
         ┌────────────────┐   ┌──────────────┐
         │ Check user     │   │ Return 401   │
         │ is_active      │   │ Unauthorized │
         └────────┬───────┘   └──────────────┘
              YES │
                  ▼
        ┌────────────────────────────────────┐
        │ Return User object                 │
        │ (get_current_user dependency)      │
        └────────┬───────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────────┐
        │ Check Role (if required)           │
        │ get_current_admin checks           │
        │ role == 'admin'                    │
        └────────┬──────────────┬────────────┘
            ADMIN │              │ NOT ADMIN
                  ▼              ▼
         ┌────────────────┐   ┌──────────────┐
         │ Proceed to     │   │ Return 403   │
         │ route handler  │   │ Forbidden    │
         └────────┬───────┘   └──────────────┘
                  │
                  ▼
        ┌────────────────────────────────────┐
        │ Check object access                │
        │ if resource.owner_id !=            │
        │    current_user.id and             │
        │    role != 'admin':                │
        │    → Return 403                    │
        └────────┬──────────────┬────────────┘
            ALLOWED │             │ DENIED
                    ▼             ▼
            ┌──────────────┐  ┌──────────────┐
            │ Execute      │  │ Return 403   │
            │ business     │  │ Forbidden    │
            │ logic        │  └──────────────┘
            │ Log action   │
            └──────┬───────┘
                   │
                   ▼
            ┌──────────────────┐
            │ Return response  │
            │ (only safe data) │
            └──────────────────┘
```

## 4. Диаграмма сценария "Просмотр счета клиентом"

```
┌──────────────────────────────────────────────────────────────────┐
│                     Customer                                      │
│  Wants to view invoice #5                                        │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       │ GET /api/billing/invoices/5
                       │ Authorization: Bearer JWT_TOKEN
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                FastAPI Application                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Parse request                                               │
│     ├─ invoice_id = 5 (validated as int)                        │
│     └─ token extracted from Authorization header                │
│                                                                  │
│  2. Dependency: get_current_user(token)                         │
│     ├─ verify_token() → decode JWT                              │
│     ├─ extract user_id from JWT payload                         │
│     ├─ SELECT * FROM users WHERE id = {user_id}                │
│     │  (Parameterized query - safe!)                            │
│     ├─ Check user.is_active == True                             │
│     └─ Return: User(id=2, username="customer1", role="customer")│
│                                                                  │
│  3. Route handler: get_invoice(invoice_id, current_user, db)   │
│     ├─ SELECT * FROM invoices WHERE id = {invoice_id}          │
│     │  (Parameterized query)                                    │
│     └─ Check if invoice exists                                  │
│                                                                  │
│  4. Authorization check                                         │
│     if invoice.user_id (2) != current_user.id (2) and          │
│        current_user.role != "admin":                            │
│         → DENIED                                                │
│     else:                                                        │
│         → ALLOWED                                               │
│                                                                  │
│  5. Logging                                                      │
│     ├─ log_audit(                                               │
│     │   action="INVOICE_VIEWED",                                │
│     │   user_id=2,                                              │
│     │   details="Invoice ID: 5, Amount: 599.99",               │
│     │   ip_address="192.168.1.100",                             │
│     │   success=True                                            │
│     │ )                                                          │
│     └─ NO passwords, tokens, emails in logs!                    │
│                                                                  │
│  6. Response serialization                                      │
│     InvoiceResponse(                                            │
│       id=5,                                                      │
│       subscription_id=1,                                         │
│       amount=599.99,                                             │
│       status="pending",                                          │
│       billing_period_start=...,                                 │
│       billing_period_end=...,                                   │
│       due_date=...,                                              │
│       created_at=...                                             │
│     )                                                            │
│     (Only whitelisted fields, NO user PII)                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                       │
                       │ HTTP 200 OK
                       │ Content-Type: application/json
                       │
                       │ {
                       │   "id": 5,
                       │   "subscription_id": 1,
                       │   "amount": 599.99,
                       │   "status": "pending",
                       │   "billing_period_start": "2026-03-11T...",
                       │   "billing_period_end": "2026-04-11T...",
                       │   "due_date": "2026-03-21T...",
                       │   "created_at": "2026-03-11T...",
                       │   "paid_at": null
                       │ }
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Customer                                      │
│  Receives invoice details                                        │
└──────────────────────────────────────────────────────────────────┘
```

## 5. Диаграмма защиты от IDOR (Insecure Direct Object Reference)

```
Сценарий: Customer 1 пытается получить счет Customer 2

Customer 1 (user_id=2) запрашивает:
GET /api/billing/invoices/10
Authorization: Bearer JWT_TOKEN_CUSTOMER1

┌──────────────────────────────────────────────────────────┐
│ 1. Аутентификация успешна                               │
│    current_user.id = 2 (Customer 1)                      │
│    current_user.role = "customer"                        │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ 2. Получить счет из БД                                  │
│    SELECT * FROM invoices WHERE id = 10                 │
│    Результат: Invoice(id=10, user_id=3, amount=...)    │
│    (invoice.user_id = 3 - это Customer 2!)              │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ 3. Проверка доступа (Object-Level Authorization)        │
│                                                          │
│    if invoice.user_id != current_user.id and \          │
│       current_user.role != "admin":                      │
│        raise HTTPException(403, "Доступ запрещен")      │
│                                                          │
│    Проверка: 3 != 2 and "customer" != "admin"           │
│    Результат: TRUE (условие выполнено)                  │
│                                                          │
│    → Выброс исключения                                  │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ 4. Логирование попытки несанкционированного доступа     │
│                                                          │
│    log_security_event(                                  │
│      event_type="unauthorized_invoice_access",          │
│      user_id=2,                                          │
│      reason="Attempted to access invoice 10 of user 3", │
│      severity="WARNING"                                  │
│    )                                                     │
│                                                          │
│    log_audit(                                            │
│      action=UNAUTHORIZED_ACCESS_ATTEMPT,                │
│      user_id=2,                                          │
│      details="Invoice ID: 10",                           │
│      ip_address="...",                                   │
│      success=False                                       │
│    )                                                     │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│ 5. Ответ: HTTP 403 Forbidden                            │
│    {                                                     │
│      "error": "Доступ запрещен"                         │
│    }                                                     │
└──────────────────────────────────────────────────────────┘
```

## 6. Диаграмма защиты от SQL-инъекции

### НЕПРАВИЛЬНО ❌ (Уязвимо)

```python
# НИКОГДА ТАК НЕ ДЕЛАЙТЕ!
user_id = request.query_params.get("user_id")
query = f"SELECT * FROM users WHERE id = {user_id}"
result = db.execute(query)

# Атака: user_id = "1 OR 1=1" → query = "SELECT * FROM users WHERE id = 1 OR 1=1"
# Результат: все пользователи выбраны!
```

### ПРАВИЛЬНО ✅ (Безопасно)

```python
# Параметризованный запрос (SQLAlchemy ORM)
user_id = int(request.path_params["user_id"])  # Валидация типа
user = db.query(User).filter(User.id == user_id).first()
# SQL: SELECT * FROM users WHERE id = ?
# Параметр user_id передается отдельно, не как часть SQL строки

# Даже если user_id содержит SQL код:
# user_id = "1 OR 1=1"
# SQL: SELECT * FROM users WHERE id = '1 OR 1=1'
# Результат: поиск пользователя с id = строка "1 OR 1=1" (не найден)
```

## 7. Матрица угроз и защиты

```
Угроза                              | Уровень   | Защита                      | Статус
────────────────────────────────────┼───────────┼─────────────────────────────┼────────
SQL Injection                       | Критичная | Параметризованные запросы   | ✅
Brute Force атаки                   | Высокая   | Лимит попыток (5 за 15м)   | ✅
Перебор пароля (слабое хеширование)| Критичная | bcrypt (автоматический salt)| ✅
Несанкционированный доступ (IDOR)  | Критичная | Object-level checks         | ✅
Компрометация токена                | Высокая   | TTL, HS256 signature        | ✅
Утечка ПДн в логах                  | Критичная | Аудит без чувствительных д. | ✅
Слабая валидация входа              | Средняя   | Pydantic + regex validation  | ✅
Информативные ошибки                | Средняя   | Нейтральные сообщения       | ✅
Hardcoded секреты                   | Критичная | .env переменные             | ✅
Уязвимости в зависимостях           | Высокая   | pip-audit, фиксированные в. | ✅
```

## 8. Граница доверия и входные точки

```
┌─────────────────────────────────────────────────────────────────┐
│                    ГРАНИЦА ДОВЕРИЯ                              │
│                                                                 │
│  Входные точки (Untrusted):                                    │
│  • HTTP запросы от клиента                                     │
│  • URL параметры                                               │
│  • Body параметры (JSON)                                       │
│  • Headers (Authorization, Content-Type, etc)                  │
│  • Query параметры                                             │
│                                                                 │
│  Обработка:                                                     │
│  1. Валидация типа (int, str, email, etc)                     │
│  2. Regex проверка формата                                     │
│  3. Range checks (min/max length, value bounds)                │
│  4. Pydantic schemas → модели привычного типа                 │
│  5. Параметризованные DB запросы                              │
│  6. Серверная проверка авторизации                            │
│  7. Логирование (без чувствительных данных)                   │
│                                                                 │
│  Доверенные источники (Internal):                              │
│  • Данные из БД (SELECT результаты)                            │
│  • Внутренние переменные приложения                            │
│  • SECRET_KEY (из .env)                                        │
│  • Конфигурация приложения                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
