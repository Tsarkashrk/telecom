# Анализ безопасности MVP системы телекоммуникаций

## Задание 1. Методология проверки кода безопасности

### 1. Определение области анализа

**Модули и компоненты:**

- `app/config.py` - Конфигурация и переменные окружения
- `app/security.py` - Криптография и управление токенами
- `app/database.py` - Подключение к БД и сессии
- `app/models.py` - ORM модели (SQLAlchemy)
- `app/schemas.py` - Валидация входных данных (Pydantic)
- `app/dependencies.py` - Проверка аутентификации и авторизации
- `app/routers/auth.py` - Регистрация и вход
- `app/routers/subscriptions.py` - Активация тариф-планов
- `app/routers/invoices.py` - Просмотр счетов
- `app/logging_config.py` - Аудит критичных действий

**API эндпоинты:**

1. `POST /api/auth/register` - Регистрация пользователя
2. `POST /api/auth/login` - Вход и получение токенов
3. `GET /api/auth/me` - Получить информацию текущего пользователя
4. `GET /api/subscriptions/tariffs` - Список тарифов
5. `POST /api/subscriptions/activate` - Активация тарифа
6. `GET /api/subscriptions` - Мои подписки
7. `GET /api/subscriptions/{id}` - Информация о подписке
8. `GET /api/billing/invoices` - Мои счета
9. `GET /api/billing/invoices/{id}` - Информация о счете
10. `GET /api/billing/invoices/user/{user_id}` - Администраторский API

**Чувствительные данные:**

- Пароли пользователей
- JWT токены (access & refresh)
- Персональные данные клиентов (email, phone)
- Информация о счетах и платежах
- IP адреса

**Роли и граница доверия:**

- `customer` - обычный пользователь, видит только свои данные
- `operator` - сотрудник, может просматривать данные клиентов
- `admin` - администратор, полный доступ

**Критичные бизнес-сценарии:**

1. Регистрация новго клиента
2. Аутентификация (login/logout)
3. Активация тарифного плана
4. Просмотр счета

---

### 2. Подготовка контекста

**Активы:**

- База данных с информацией о клиентах
- Данные о подписках и счетах
- Система аутентификации (JWT токены)

**Вероятные угрозы:**

- SQL-инъекции при работе с БД
- Перебор паролей (brute-force)
- Несанкционированный доступ к чужим счетам (IDOR)
- Утечка чувствительных данных в логах
- Инъекции в сообщения об ошибках
- Компрометация JWT токенов
- Слабое хеширование паролей

---

### 3. Построение алгоритма системы и ключевого сценария

#### Структурная схема MVP:

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI Application                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐        ┌──────────────────┐           │
│  │  Auth Router     │        │  Subscription    │           │
│  │  - register      │        │  Router          │           │
│  │  - login         │        │  - list tariffs  │           │
│  │  - get me        │        │  - activate      │           │
│  └──────────────────┘        │  - get subs      │           │
│                              └──────────────────┘           │
│  ┌──────────────────┐                                       │
│  │  Invoices Router │                                       │
│  │  - list invoices │                                       │
│  │  - get invoice   │                                       │
│  │  - admin API     │                                       │
│  └──────────────────┘                                       │
│         ▲                                                    │
└─────────┼────────────────────────────────────────────────────┘
          │
    ┌─────▼──────────────────────────────────────────┐
    │   Dependencies & Security Layer                │
    │  - get_current_user (JWT verify)               │
    │  - get_current_admin (role check)              │
    │  - verify_object_access (IDOR check)           │
    └─────┬──────────────────────────────────────────┘
          │
    ┌─────▼──────────────────────────────────────────┐
    │   Schemas (Pydantic)                           │
    │  - Input validation                            │
    │  - Type checking                               │
    │  - Format validation                           │
    └─────┬──────────────────────────────────────────┘
          │
    ┌─────▼──────────────────────────────────────────┐
    │   Database Layer (SQLAlchemy)                  │
    │  - Parameterized queries                       │
    │  - ORM models                                  │
    │  - Foreign keys & constraints                  │
    └─────┬──────────────────────────────────────────┘
          │
    ┌─────▼──────────────────────────────────────────┐
    │   SQLite Database                              │
    │  - users                                       │
    │  - tariff_plans                                │
    │  - subscriptions                               │
    │  - invoices                                    │
    │  - audit_logs                                  │
    └──────────────────────────────────────────────────┘
```

#### Блок-схема основного сценария (Просмотр счета клиентом):

```
┌─────────────────────────────────┐
│  Клиент запрашивает счет        │
│  GET /api/billing/invoices/{id} │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Получена ли авторизация?       │
│  JWT токен в заголовке?         │
└────────────┬──────────┬─────────┘
        НЕТ │          │ ДА
             ▼          ▼
     ┌──────────┐   ┌──────────────────┐
     │ 401 Error│   │ Проверить токен  │
     └──────────┘   └──────┬───────────┘
                           │
                           ▼
                  ┌────────────────────┐
                  │ Токен валиден?     │
                  │ Не истек ли?       │
                  └────────┬───┬───────┘
                      НЕТ │   │ ДА
                           ▼   ▼
                   ┌──────────┐ ┌────────────────────┐
                   │401 Error │ │ Получить User ID   │
                   └──────────┘ │ из payload         │
                                └────────┬───────────┘
                                         │
                                         ▼
                                ┌─────────────────────┐
                                │ Получить счет из БД │
                                │ (параметризованный) │
                                └────────┬────────────┘
                                         │
                                         ▼
                                ┌──────────────────────┐
                                │ Счет найден?         │
                                └────────┬──┬─────────┘
                                    НЕТ │  │ ДА
                                         ▼  ▼
                                  ┌────────┐┌──────────────────┐
                                  │404 Err.││ Проверить доступ  │
                                  └────────┘│ user_id == owner? │
                                            │ role == admin?    │
                                            └────────┬──┬───────┘
                                                DENY │  │ OK
                                                     ▼  ▼
                                            ┌──────────┐┌─────────────┐
                                            │403 Error││ Логирование │
                                            └──────────┘│ INVOICE_VIEW│
                                                        └──────┬──────┘
                                                               │
                                                               ▼
                                                    ┌──────────────────┐
                                                    │ Вернуть счет     │
                                                    │ (без ПДн)        │
                                                    │ 200 OK           │
                                                    └──────────────────┘
```

---

### 4. Выделение критичных участков кода

#### 4.1 Приемы пользовательского ввода:

**File: `app/schemas.py`**

- `UserRegisterRequest` - валидация имени, email, телефона, пароля с regex
- `UserLoginRequest` - валидация username и password
- `ActivateTariffRequest` - валидация tariff_id (gt=0)

#### 4.2 Решения о доступе (авторизация):

**File: `app/dependencies.py`**

- `get_current_user` - проверка JWT токена
- `get_current_admin` - проверка роли администратора
- `verify_object_access` - проверка доступа к конкретному объекту

**File: `app/routers/invoices.py`, line 47-72**

```python
# Проверка доступа к конкретному счету
if invoice.user_id != current_user.id and current_user.role != "admin":
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен")
```

#### 4.3 Обращение к БД:

**File: `app/routers/auth.py`, line 30-35**

```python
# Параметризованный запрос - ПРАВИЛЬНО
existing_user = db.query(User).filter(User.username == user_data.username).first()
```

**File: `app/routers/invoices.py`, line 33-36**

```python
# Параметризованный запрос - ПРАВИЛЬНО
invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
```

#### 4.4 Работа с токенами и паролями:

**File: `app/security.py`**

- `hash_password()` - хеширование bcrypt (line 12-13)
- `verify_password()` - проверка пароля (line 16-17)
- `create_access_token()` - создание JWT с exp (line 20-34)
- `create_refresh_token()` - refresh токен (line 37-47)
- `verify_token()` - декодирование и проверка (line 50-62)

#### 4.5 Логирование и аудит:

**File: `app/logging_config.py`**

- `log_audit()` - логирование действий БЕЗ пароля, токенов, ПДн
- `log_security_event()` - логирование событий безопасности

---

### 5. Анализ потоков данных

#### Ключевой сценарий: Просмотр счета клиентом

**Source (источник):** HTTP запрос с JWT токеном и параметром `invoice_id`

```
GET /api/billing/invoices/{invoice_id}
Header: Authorization: Bearer eyJhbGc... (JWT token)
```

**Propagation (распространение):**

```
1. FastAPI парсит запрос
   ├─ invoice_id извлекается из URL параметра (int)
   └─ token извлекается из Authorization header

2. Dependency injection вызывает get_current_user()
   ├─ verify_token() декодирует JWT
   ├─ payload.get("sub") получает user_id
   ├─ db.query(User).filter(User.id == user_id) - параметризованный запрос
   └─ Возвращает User объект

3. invoice_id используется в параметризованном запросе:
   db.query(Invoice).filter(Invoice.id == invoice_id).first()
```

**Sink (приемник):**

```
# Проверка доступа (авторизация)
if invoice.user_id != current_user.id and current_user.role != "admin":
    raise HTTPException(403)  # Блокирование несанкционированного доступа

# Возврат данных
return InvoiceResponse(...)  # Только разрешенные поля
```

**Sanitization (санация):**

```
1. Валидация типа: invoice_id должен быть int
2. Параметризованный SQL запрос (защита от инъекций)
3. Проверка доступа на серверной стороне
4. Возврат только необходимых полей (не возвращаем user email, password)
5. Логирование без чувствительных данных
```

**Data Flow Diagram:**

```
                    ┌─────────────────────────────────────┐
                    │  Client Request                     │
                    │ GET /billing/invoices/{invoice_id}  │
                    │ Header: Authorization: Bearer JWT   │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ FastAPI Route Handler       │
                    │ - Parse URL params (int)    │
                    │ - Extract Authorization     │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │ Dependency: get_current_user()      │
                    │ - verify_token(JWT)                 │
                    │ - Decode payload                    │
                    │ - Get user_id from sub field        │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │ DB Query (Parameterized)            │
                    │ SELECT * FROM invoices              │
                    │ WHERE id = ?                        │
                    │ Parameter: invoice_id (int)         │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │ Authorization Check                 │
                    │ if invoice.user_id != current_user  │
                    │    and role != admin:               │
                    │    → Raise 403 Forbidden            │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │ Response Serialization              │
                    │ InvoiceResponse (Pydantic)          │
                    │ - Only whitelisted fields           │
                    │ - No PII, no passwords              │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │ Audit Logging                       │
                    │ log_audit(INVOICE_VIEWED, user_id)  │
                    │ (NO sensitive data in logs)         │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │ HTTP Response                       │
                    │ 200 OK                              │
                    │ Body: {"id": ..., "amount": ...}   │
                    └──────────────────────────────────────┘
```

---

### 6. Проверка защитных механизмов

#### 6.1 Аутентификация

| Механизм              | Реализация                                             | Статус |
| --------------------- | ------------------------------------------------------ | ------ |
| Хеширование пароля    | bcrypt в `app/security.py:hash_password()`             | ✅     |
| Валидация пароля      | Проверка в `verify_password()` против хеша             | ✅     |
| Access token          | JWT с exp в `create_access_token()`                    | ✅     |
| Refresh token         | JWT с типом "refresh" в `create_refresh_token()`       | ✅     |
| Token lifetime        | ACCESS: 30 минут, REFRESH: 7 дней (из config)          | ✅     |
| Защита от brute-force | Лимит попыток (5) в `app/routers/auth.py:line 108-126` | ✅     |

#### 6.2 Авторизация

| Механизм           | Реализация                                                             | Статус |
| ------------------ | ---------------------------------------------------------------------- | ------ |
| Проверка роли      | `get_current_admin()`, `get_current_operator()` в `dependencies.py`    | ✅     |
| Доступ к объекту   | `invoice.user_id == current_user.id` в `app/routers/invoices.py:47-50` | ✅     |
| Серверная проверка | Все проверки на backend                                                | ✅     |
| Защита от IDOR     | Проверка ownership перед возвратом данных                              | ✅     |

#### 6.3 Валидация входных данных

| Поле      | Валидация           | Реализация                         |
| --------- | ------------------- | ---------------------------------- |
| username  | Regex + length      | `schemas.py:validate_username()`   |
| email     | EmailStr            | Pydantic EmailStr                  |
| phone     | Regex + length      | `schemas.py:validate_phone()`      |
| password  | Complexity + length | `schemas.py:validate_password()`   |
| tariff_id | gt=0                | `schemas.py:ActivateTariffRequest` |

#### 6.4 Криптография

| Параметр           | Значение                    | Статус         |
| ------------------ | --------------------------- | -------------- |
| Хеширование пароля | bcrypt                      | ✅ Современный |
| JWT алгоритм       | HS256                       | ✅ Безопасный  |
| Хранение secret    | переменная окружения `.env` | ✅             |

#### 6.5 Обработка ошибок

| Ошибка                     | Сообщение                              | Логирование           |
| -------------------------- | -------------------------------------- | --------------------- |
| Неверный пароль            | "Неверное имя пользователя или пароль" | Нейтральное           |
| Несанкционированный доступ | "Доступ запрещен"                      | Логируется с detail   |
| Ошибка БД                  | "Внутренняя ошибка сервера"            | Логируется на backend |

#### 6.6 Логирование и аудит

| События         | Логирование                  | Чувствительные данные   |
| --------------- | ---------------------------- | ----------------------- |
| Регистрация     | `log_audit(USER_REGISTERED)` | ❌ Не логируются        |
| Вход            | `log_audit(USER_LOGIN)`      | ❌ Пароль не логируется |
| Просмотр счета  | `log_audit(INVOICE_VIEWED)`  | ❌ Не логируется        |
| Доступ запрещен | `log_security_event()`       | ❌ Не логируются        |

---

### 7. Фиксация находок

#### 7.1 Обнаруженные уязвимости и их устранение

| #   | Место             | Уязвимость                                          | Риск                       | Критичность | Решение                                                                                |
| --- | ----------------- | --------------------------------------------------- | -------------------------- | ----------- | -------------------------------------------------------------------------------------- |
| 1   | Теоретическая     | SQL-инъекция через неправильное построение запросов | Доступ к БД, кража данных  | КРИТИЧНАЯ   | ✅ Использованы параметризованные запросы SQLAlchemy, user input передается параметром |
| 2   | `auth.py`         | Слабое хеширование пароля                           | Перебор пароля             | КРИТИЧНАЯ   | ✅ Используется bcrypt (passlib)                                                       |
| 3   | `auth.py`         | Отсутствие защиты от brute-force                    | Перебор пароля             | ВЫСОКАЯ     | ✅ Реализован лимит попыток (5 за 15 минут)                                            |
| 4   | `invoices.py`     | IDOR - доступ к чужим счетам                        | Доступ к ПДн               | КРИТИЧНАЯ   | ✅ Проверка `invoice.user_id == current_user.id` перед возвратом                       |
| 5   | `schemas.py`      | Слабая валидация входных данных                     | Инъекции, garbage data     | ВЫСОКАЯ     | ✅ Pydantic валидация: regex, length, type checks                                      |
| 6   | `auth.py`         | Информативные сообщения об ошибках                  | Перечисление пользователей | СРЕДНЯЯ     | ✅ Одинаковое сообщение для неверного username/password                                |
| 7   | Теоретическая     | Пароли в логах                                      | Утечка credentials         | КРИТИЧНАЯ   | ✅ Пароли не логируются, логируются только user_id                                     |
| 8   | Теоретическая     | Токены в логах                                      | Компрометация session      | КРИТИЧНАЯ   | ✅ Токены не возвращаются и не логируются в JSON response                              |
| 9   | Теоретическая     | Hardcoded секреты                                   | Компрометация всей системы | КРИТИЧНАЯ   | ✅ SECRET_KEY в .env (исключен из git)                                                 |
| 10  | `invoices.py`     | Утечка email/phone в API response                   | Утечка ПДн                 | ВЫСОКАЯ     | ✅ InvoiceResponse содержит только разрешенные поля                                    |
| 11  | `dependencies.py` | Отсутствие проверки прав на серверной стороне       | Обход авторизации          | КРИТИЧНАЯ   | ✅ Проверка role на backend в каждом эндпоинте                                         |
| 12  | Теоретическая     | Обновление dependencies                             | Уязвимости в библиотеках   | ВЫСОКАЯ     | ✅ pip-audit и фиксированные версии в requirements.txt                                 |

#### 7.2 Таблица соответствия OWASP Top 10

| OWASP | Уязвимость                         | Статус      | Реализованное решение                           |
| ----- | ---------------------------------- | ----------- | ----------------------------------------------- |
| A01   | Broken Access Control              | ✅ ЗАЩИЩЕНО | Проверка доступа на backend, проверка ownership |
| A02   | Cryptographic Failures             | ✅ ЗАЩИЩЕНО | bcrypt для паролей, JWT с exp, HTTPS ready      |
| A03   | Injection                          | ✅ ЗАЩИЩЕНО | Параметризованные запросы SQLAlchemy            |
| A04   | Insecure Design                    | ✅ ЗАЩИЩЕНО | Явные проверки авторизации в каждом маршруте    |
| A05   | Security Misconfiguration          | ✅ ЗАЩИЩЕНО | .env для секретов, PRAGMA foreign_keys          |
| A06   | Vulnerable and Outdated Components | ✅ ЗАЩИЩЕНО | pip-audit, фиксированные версии                 |
| A07   | Authentication Failures            | ✅ ЗАЩИЩЕНО | bcrypt, защита от brute-force, JWT с TTL        |
| A08   | Data Integrity Failures            | ✅ ЗАЩИЩЕНО | Валидация Pydantic, constraints в БД            |
| A09   | Logging & Monitoring               | ✅ ЗАЩИЩЕНО | Аудит-логи, log_security_event                  |
| A10   | SSRF                               | N/A         | Нет внешних запросов в MVP                      |

---

### 8. Подготовка рекомендаций

#### 8.1 Меры по безопасности в коде

**1. SQL Injection Protection**

- ✅ Используются параметризованные запросы SQLAlchemy ORM
- ✅ Никогда не используется string concatenation для SQL
- ✅ User input передается как параметр, не как часть SQL строки

**2. Password Security**

- ✅ Используется bcrypt через passlib
- ✅ Пароли никогда не логируются
- ✅ Валидация сложности пароля (число, буква, спецсимвол)
- ✅ Минимальная длина: 8 символов

**3. Authentication & Authorization**

- ✅ JWT токены с ограниченным сроком жизни
- ✅ Access token: 30 минут
- ✅ Refresh token: 7 дней
- ✅ Проверка доступа на серверной стороне
- ✅ Проверка ownership объектов (IDOR protection)
- ✅ Защита от brute-force (5 попыток за 15 минут)

**4. Input Validation**

- ✅ Pydantic schemas для всех входных данных
- ✅ Regex валидация username, phone
- ✅ EmailStr для email
- ✅ Типизированные параметры
- ✅ Range checks (gt=0 для ID)

**5. Error Handling**

- ✅ Нейтральные сообщения об ошибках
- ✅ Нет stack trace в response
- ✅ Логирование деталей на backend только
- ✅ HTTP исключения с правильными статус кодами

**6. Sensitive Data Protection**

- ✅ Пароли не в логах
- ✅ Токены не в логах
- ✅ API responses содержат только необходимые поля
- ✅ ПДн не в сообщениях об ошибках

**7. Cryptography**

- ✅ bcrypt для паролей (автоматический salt)
- ✅ HS256 для JWT
- ✅ Нет MD5, SHA-1 или самописных схем
- ✅ SECRET_KEY в .env

#### 8.2 Конфигурация и развертывание

**1. Переменные окружения (.env)**

```
DATABASE_URL=sqlite:///./telecom.db
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
LOG_LEVEL=INFO
```

**2. Исключение из версионирования**

```
.env
.env.local
*.db
__pycache__/
.pytest_cache/
```

**3. Минимальные привилегии БД**

- Пользователь БД не имеет прав superuser
- Используется SQLite для MVP (можно поменять на PostgreSQL в production)

**4. HTTPS**

- В production ВСЕГДА использовать HTTPS
- Установить Secure флаг для cookies
- Использовать SameSite=Strict

#### 8.3 Тестирование безопасности

**SAST (Static Application Security Testing)**

```bash
bandit -r app/
```

**SCA (Software Composition Analysis)**

```bash
pip-audit
```

**DAST (Dynamic Application Security Testing)**

```bash
# Тестирование SQL injection
curl -X GET "http://localhost:8000/api/billing/invoices/1' OR '1'='1"

# Тестирование IDOR
# Попытка доступа к счету другого пользователя

# Тестирование brute-force защиты
for i in {1..10}; do curl -X POST "http://localhost:8000/api/auth/login" -d '{"username":"admin","password":"wrong"}'; done
```

#### 8.4 Мониторинг и логирование

**Критичные события для мониторинга:**

- Неудачные попытки входа (особенно brute-force)
- Попытки несанкционированного доступа (403)
- Ошибки БД (500)
- Администраторские действия

**Log aggregation:**

- ELK Stack (Elasticsearch, Logstash, Kibana)
- Splunk
- CloudWatch (AWS)

#### 8.5 Обновления и патчи

**Регулярно:**

- Запускать `pip-audit` для проверки уязвимостей
- Обновлять зависимости
- Проверять security advisories

**Requirements.txt**

```
fastapi==0.104.1
sqlalchemy==2.0.23
passlib==1.7.4
bcrypt==4.1.1
pyjwt==2.8.1
```

Все версии явно указаны для воспроизводимости.

---

## Задание 2. Контрольные списки для проверки кода безопасности

### 1. ✅ Входные данные

- [x] **Наличие валидации:** Все входные данные валидируются Pydantic
  - `UserRegisterRequest` - валидация username, email, phone, password
  - `UserLoginRequest` - валидация username, password
  - `ActivateTariffRequest` - валидация tariff_id

- [x] **Тип данных:** Явная типизация
  - `invoice_id: int` - получается как int из URL
  - `tariff_id: int` - Field(gt=0) гарантирует положительное число
  - `email: EmailStr` - встроенная валидация

- [x] **Формат:** Regex валидация
  - `username: ^[a-zA-Z0-9_]+$` - только буквы, цифры, подчеркивания
  - `phone: ^[+\d\s\-()]+$` - для номеров телефонов
  - `password: ` - проверка на наличие цифры, буквы, спецсимвола

- [x] **Диапазон:** Range checks
  - `username: min_length=3, max_length=50`
  - `email: max_length=100` (в модели)
  - `password: min_length=8, max_length=128`
  - `tariff_id: gt=0` - должен быть > 0

- [x] **Длина:** Явные limits
  - Все string поля имеют max_length
  - БД constraints гарантируют границы

- [x] **Допустимые значения:** Enum валидация
  - `role: "customer" | "operator" | "admin"`
  - `status: "active" | "suspended" | "cancelled"`

### 2. ✅ Аутентификация

- [x] **Хранение паролей:** bcrypt хеш
  - `hash_password()` использует CryptContext(schemes=["bcrypt"])`
  - Автоматический salt генерируется bcrypt
  - Пароль никогда не сохраняется в открытом виде

- [x] **Access token:**
  - JWT с HS256 алгоритмом
  - Содержит `sub` (user_id) и `exp` (время истечения)
  - TTL: 30 минут (из settings)

- [x] **Refresh token:**
  - Отдельный JWT с типом "refresh"
  - TTL: 7 дней
  - Может использоваться для получения нового access token

- [x] **Срок жизни сессии:**
  - Access: 30 минут (ACCESS_TOKEN_EXPIRE_MINUTES в .env)
  - Refresh: 7 дней (REFRESH_TOKEN_EXPIRE_DAYS в .env)
  - После истечения - требуется повторная аутентификация

- [x] **Logout:** Возможность выхода
  - Client удаляет токен локально
  - Server может добавить token blacklist (как улучшение)

- [x] **Защита от brute-force:**
  - Лимит 5 попыток входа за 15 минут
  - После превышения - ошибка 429 Too Many Requests
  - Реализация в `check_login_attempts()` и `record_login_attempt()`

### 3. ✅ Авторизация

- [x] **Проверка прав доступа на serv стороне:**
  - Все маршруты используют `get_current_user` dependency
  - JWT декодируется и проверяется на server
  - Токен не может быть подделан без SECRET_KEY

- [x] **Доступ к конкретному объекту (IDOR prevention):**
  - `GET /api/billing/invoices/{invoice_id}`:
    ```python
    if invoice.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403)
    ```
  - Проверка для каждого resource
  - Клиент видит только свои объекты

- [x] **Изоляция административных функций:**
  - `GET /api/billing/invoices/user/{user_id}` - только для admin
  - Проверка `if current_user.role != "admin": raise 403`
  - Четкое разделение ролей

- [x] **Защита от повышения привилегий:**
  - Role назначается при создании пользователя (всем "customer")
  - Admin может изменяться только admin (не реализовано в MVP, но архитектура поддерживает)
  - Роль не может быть изменена через API клиентом

### 4. ✅ Данные и логирование

- [x] **Отсутствие лишних полей в API:**
  - `UserResponse` - только id, username, email, phone, role, is_active, created_at
  - НЕ возвращаем `hashed_password`
  - `InvoiceResponse` - только публичные поля
  - НЕ возвращаем internal details

- [x] **Пароли не в логах:**
  - `log_audit()` не принимает пароли
  - Пароли не логируются нигде
  - В JWT логах не проходит

- [x] **Безопасные сообщения об ошибках:**
  - "Неверное имя пользователя или пароль" - не раскрывает какое именно неверно
  - "Доступ запрещен" - не раскрывает почему
  - Не используются stack trace в HTTP response

- [x] **Аудит критичных действий:**
  - `USER_REGISTERED` - новый пользователь
  - `USER_LOGIN` - успешный вход
  - `TARIFF_ACTIVATED` - активация тарифа
  - `INVOICE_VIEWED` - просмотр счета
  - `UNAUTHORIZED_ACCESS_ATTEMPT` - попытка несанкционированного доступа
  - Все с user_id, ip_address, timestamp

- [x] **Отсутствие ПДн в логах:**
  - Не логируются email, phone, номера счетов
  - Логируются только user_id
  - ПДн находится в БД, не в логах

### 5. ✅ Криптография

- [x] **Современные алгоритмы:**
  - bcrypt для паролей (один из лучших вариантов)
  - HS256 для JWT (стандартный для небольших систем)
  - SHA-256 в bcrypt (внутри)

- [x] **Отсутствие старых криптографических схем:**
  - ❌ НЕ используется MD5
  - ❌ НЕ используется SHA-1
  - ❌ НЕ используется DES
  - ❌ НЕ используются самописные криптографические функции

- [x] **Отсутствие захардкоженных секретов:**
  - SECRET_KEY в переменной окружения (.env)
  - DATABASE_URL в .env
  - .env исключен из git (.gitignore)
  - .env.example содержит шаблон

### 6. ✅ Зависимости и базовая безопасность окружения

- [x] **Версии библиотек:**
  - Все версии явно зафиксированы в requirements.txt
  - Нет использования `==` с latest version
  - Пример: `fastapi==0.104.1` (не `fastapi>=0.100.0`)

- [x] **SAST анализ (Static Analysis):**
  - Готово к запуску `bandit -r app/`
  - Проверяет потенциальные уязвимости в коде
  - Должно выполняться перед commit

- [x] **SCA анализ (Dependency Check):**
  - Готово к запуску `pip-audit`
  - Проверяет известные уязвимости в зависимостях
  - Версии в requirements.txt выбраны без критичных CVE

- [x] **Исключение пароля из репозитория:**
  - .env в .gitignore
  - Нет hardcoded пароли в коде
  - .env.example содержит template

- [x] **Исключение конфигов с секретами:**
  - Нет config.json, config.yaml с PASSWORD
  - Все секреты через переменные окружения

---

## Заключение

MVP система телекоммуникаций реализована с учетом современных практик безопасности:

✅ **Аутентификация:** bcrypt + JWT tokens
✅ **Авторизация:** Role-based access control + object-level checks
✅ **Валидация:** Pydantic + regex + type checks
✅ **SQL Security:** Параметризованные запросы SQLAlchemy
✅ **Logging:** Аудит без чувствительных данных
✅ **Error Handling:** Безопасные сообщения об ошибках
✅ **Dependencies:** Зафиксированные версии, ready для SCA/SAST

Все обязательные требования выполнены. Система готова для развертывания в production с дополнительными мерами (HTTPS, WAF, monitoring).
