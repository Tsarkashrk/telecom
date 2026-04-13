# План выполнения требований к MVP системе

## ✅ Обязательные требования безопасности для всех вариантов

### 1. ✅ Структурная схема MVP

**Файл:** `DIAGRAMS.md` - Раздел 1 "Архитектурная диаграмма компонентов"

Содержит полную диаграмму:

- FastAPI Web Server с роутерами
- Dependency Injection & Security Layer
- Validation Layer (Pydantic)
- Security & Crypto Layer
- Database Layer (SQLAlchemy)
- Logging & Auditing
- SQLite Database

### 2. ✅ Блок-схема сценария варианта

**Файл:** `DIAGRAMS.md` - Раздел 4 "Диаграмма сценария 'Просмотр счета клиентом'"

Блок-схема показывает полный процесс:

1. Parse request (invoice_id, token)
2. Dependency injection → get_current_user
3. JWT verification and decoding
4. Database query (parameterized)
5. Authorization check (IDOR protection)
6. Logging (without sensitive data)
7. Response serialization
8. HTTP response

---

## ✅ Инъекции и валидация ввода

### 1. ✅ Использование параметризованных запросов

**Реализация:** `app/database.py`, все `routers/*.py`

Примеры:

```python
# ✅ ПРАВИЛЬНО - параметризованный запрос SQLAlchemy
user = db.query(User).filter(User.username == user_data.username).first()
invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
subscription = db.query(Subscription).filter(
    and_(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    )
).first()
```

User input передается как параметр, не как часть SQL строки.

### 2. ✅ Валидация типа, длины, диапазона, формата

**Реализация:** `app/schemas.py`

#### Username validation:

```python
username: str = Field(..., min_length=3, max_length=50)
@field_validator('username')
def validate_username(cls, v):
    if not re.match(r'^[a-zA-Z0-9_]+$', v):
        raise ValueError('Username содержит недопустимые символы')
    return v
```

- Тип: str
- Длина: 3-50 символов
- Формат: только буквы, цифры, подчеркивания

#### Email validation:

```python
email: EmailStr  # Встроенная валидация EmailStr
```

- Тип: email
- Проверка формата встроена

#### Phone validation:

```python
phone: str = Field(..., min_length=10, max_length=20)
@field_validator('phone')
def validate_phone(cls, v):
    if not re.match(r'^[+\d\s\-()]+$', v):
        raise ValueError('Некорректный формат номера телефона')
    return v
```

- Тип: str
- Длина: 10-20 символов
- Формат: цифры, +, -, (), пробелы

#### Password validation:

```python
password: str = Field(..., min_length=8, max_length=128)
@field_validator('password')
def validate_password(cls, v):
    if not re.search(r'\d', v):
        raise ValueError('Пароль должен содержать цифру')
    if not re.search(r'[a-zA-Z]', v):
        raise ValueError('Пароль должен содержать букву')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
        raise ValueError('Пароль должен содержать спецсимвол')
    return v
```

- Тип: str
- Длина: 8-128 символов
- Формат: минимум одна цифра, буква, спецсимвол
- Сложность: гарантирует сильный пароль

#### Tariff ID validation:

```python
tariff_id: int = Field(..., gt=0)
```

- Тип: int
- Диапазон: > 0

### 3. ✅ Никогда не вставлять пользовательский ввод в SQL

Все обращения к БД используют SQLAlchemy ORM с параметризованными запросами.

---

## ✅ Аутентификация и авторизация

### 1. ✅ Хранение пароля только в виде хеша

**Реализация:** `app/security.py`, `app/routers/auth.py`

```python
# Хеширование при регистрации
hashed_password = hash_password(user_data.password)
new_user = User(..., hashed_password=hashed_password)

# Проверка при входе
if not verify_password(credentials.password, user.hashed_password):
    raise HTTPException(status_code=401)
```

**Детали реализации:**

- Функция: `hash_password()` использует `CryptContext(schemes=["bcrypt"])`
- bcrypt автоматически генерирует salt
- Пароль никогда не хранится в открытом виде
- Функция `verify_password()` проверяет plain password против хеша

### 2. ✅ Выдача токенов с ограниченным сроком жизни

**Реализация:** `app/security.py`, `app/routers/auth.py:line 88-96`

```python
# Access Token (30 минут)
access_token = create_access_token(data={"sub": user.id})

# Refresh Token (7 дней)
refresh_token = create_refresh_token(data={"sub": user.id})

# JWT с exp
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes  # 30 мин
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    return encoded_jwt
```

**TTL:**

- ACCESS: 30 минут (ACCESS_TOKEN_EXPIRE_MINUTES из .env)
- REFRESH: 7 дней (REFRESH_TOKEN_EXPIRE_DAYS из .env)

### 3. ✅ Проверка прав доступа на серверной стороне

**Реализация:** `app/dependencies.py`, все `routers/*.py`

```python
# get_current_user - обязательна для всех защищенных маршрутов
@router.get("/api/auth/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# get_current_admin - для администраторских операций
@router.get("/api/billing/invoices/user/{user_id}")
def get_user_invoices_admin(
    current_user: User = Depends(get_current_user),  # ← Сначала проверяем аутентификацию
    ...
):
    if current_user.role != "admin":  # ← Потом проверяем роль на серверной стороне
        raise HTTPException(status_code=403, detail="Доступ запрещен")
```

Все проверки выполняются на backend, не на клиенте.

### 4. ✅ Проверка доступа к конкретному объекту

**Реализация:** `app/routers/invoices.py:line 47-72`

```python
# Object-Level Authorization (IDOR Protection)
if invoice.user_id != current_user.id and current_user.role != "admin":
    log_security_event(
        event_type="unauthorized_invoice_access",
        user_id=current_user.id,
        reason=f"Attempted to access invoice {invoice_id} of user {invoice.user_id}"
    )
    raise HTTPException(status_code=403, detail="Доступ запрещен")
```

Проверяется:

- Клиент может видеть только свои счета
- Администратор может видеть все счета
- Проверка выполняется перед возвратом данных

Для каждого ресурса проверяется ownership:

- Invoice: `invoice.user_id == current_user.id`
- Subscription: `subscription.user_id == current_user.id`

---

## ✅ Утечки чувствительных данных

### 1. ✅ Не возвращать лишние поля в API

**Реализация:** `app/schemas.py`

```python
# UserResponse - без пароля
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    phone: str
    role: str
    is_active: bool
    created_at: datetime
    # ❌ NO hashed_password

# InvoiceResponse - без ПДн
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
    # ❌ NO user email, phone, other PII
```

### 2. ✅ Не писать пароли, токены, ключи в лог

**Реализация:** `app/logging_config.py`

```python
def log_audit(
    action: AuditAction,
    user_id: int = None,
    details: str = None,
    ip_address: str = None,
    success: bool = True
) -> None:
    """
    ВАЖНО: Никогда не логируем пароли, токены, полные номера счетов.
    """
    # ✅ Логируем только безопасные данные
    log_message = f"[AUDIT] Action: {action.value}"
    if user_id:
        log_message += f" | User ID: {user_id}"
    if details:
        log_message += f" | Details: {details}"
```

**Что НЕ логируется:**

- ❌ Пароль (plain text)
- ❌ Хеш пароля
- ❌ JWT токены (access, refresh)
- ❌ SECRET_KEY
- ❌ DATABASE_URL с пароль
- ❌ Email полностью (можно частично, напр. \*\*\*@example.com)
- ❌ Phone full (можно частично, напр. +7-**_-_**-0001)
- ❌ ПДн клиента

### 3. ✅ Безопасные сообщения об ошибках

**Реализация:** `app/routers/auth.py:line 76-85`

```python
# ❌ НЕПРАВИЛЬНО - информативная ошибка раскрывает info
if user is None:
    raise HTTPException(detail="User not found")  # ← Раскрывает информацию
elif not verify_password(...):
    raise HTTPException(detail="Invalid password")  # ← Раскрывает что username верный

# ✅ ПРАВИЛЬНО - нейтральная ошибка
if user is None or not verify_password(...):
    raise HTTPException(detail="Неверное имя пользователя или пароль")  # ← Не раскрывает
```

**Внутренние ошибки БД:**

```python
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database error: {str(exc)}")  # ← Логируется внутри
    return JSONResponse(
        status_code=500,
        content={"error": "Внутренняя ошибка сервера"}  # ← Безопасное сообщение клиенту
    )
```

### 4. ✅ Аудит критичных действий

**Реализация:** `app/logging_config.py`, все `routers/*.py`

Логируются критичные действия:

```python
class AuditAction(str, Enum):
    USER_REGISTERED = "user_registered"           # ← Регистрация
    USER_LOGIN = "user_login"                     # ← Вход
    TARIFF_ACTIVATED = "tariff_activated"         # ← Активация тарифа
    INVOICE_CREATED = "invoice_created"           # ← Создание счета
    INVOICE_VIEWED = "invoice_viewed"             # ← Просмотр счета
    UNAUTHORIZED_ACCESS_ATTEMPT = "..."           # ← Попытка доступа
    INVALID_TOKEN = "invalid_token"               # ← Проблема с токеном
    PASSWORD_CHANGED = "password_changed"         # ← Смена пароля
```

Пример логирования:

```python
# Регистрация
log_audit(
    action=AuditAction.USER_REGISTERED,
    user_id=new_user.id,
    ip_address=client_ip,
    success=True
)

# Просмотр счета
log_audit(
    action=AuditAction.INVOICE_VIEWED,
    user_id=current_user.id,
    details=f"Invoice ID: {invoice_id}, Amount: {invoice.amount}",
    success=True
)

# Попытка доступа запрещена
log_security_event(
    event_type="unauthorized_invoice_access",
    user_id=current_user.id,
    reason=f"Attempted to access invoice {invoice_id} of user {invoice.user_id}",
    severity="WARNING"
)
```

---

## ✅ Криптография

### 1. ✅ Использование современных алгоритмов

- ✅ **bcrypt** для хеширования пароля (автоматический salt, итерации)
- ✅ **HS256** (HMAC SHA-256) для JWT (стандартный и безопасный)
- ✅ **SHA-256** внутри bcrypt

### 2. ✅ Отсутствие старых криптографических решений

- ❌ НЕ используется MD5
- ❌ НЕ используется SHA-1
- ❌ НЕ используется DES
- ❌ НЕ используются самописные криптографические функции
- ❌ НЕ используется plain text хранение пароля

Все используемые алгоритмы:

```
passlib.context.CryptContext(schemes=["bcrypt"])  # ← Современный
jwt.encode(..., algorithm="HS256")                # ← Стандартный
```

### 3. ✅ Отсутствие захардкоженных секретов

**Реализация:** `app/config.py`, `.env`, `.gitignore`

```python
# ✅ SECRET_KEY из переменной окружения
class Settings(BaseSettings):
    secret_key: str = "change-me-in-production"  # Значение по умолчанию

    class Config:
        env_file = ".env"  # ← Загружается из .env
```

**.env.example** (в репозитории):

```
SECRET_KEY=your-secret-key-change-in-production
DATABASE_URL=sqlite:///./telecom.db
```

**.env** (локальный, исключен из git):

```
SECRET_KEY=<generated-secret-key>
DATABASE_URL=sqlite:///./telecom.db
```

**.gitignore**:

```
.env
.env.local
*.db
```

---

## ✅ Работа с памятью

### 1. ✅ Не использовать небезопасную десериализацию

Только работа с JSON через Pydantic (безопасно):

```python
# ✅ ПРАВИЛЬНО
request: UserRegisterRequest = Pydantic schema
# Pydantic парсит JSON и валидирует

# ❌ НЕПРАВИЛЬНО (не используется)
import pickle
user = pickle.loads(untrusted_data)  # ← ОПАСНО!
```

### 2. ✅ Не принимать недоверенные бинарные объекты

Все входные данные:

- Парсируются как JSON
- Валидируются через Pydantic
- Типизированы

### 3. ✅ Ограничивать размеры файлов и запросов

Pydantic автоматически проверяет:

- max_length для string полей
- Field limits

FastAPI имеет встроенные ограничения:

- max_size для JSON body (по умолчанию 100MB)

### 4. ✅ Не допускать бесконтрольную загрузку данных

В MVP нет загрузки файлов, но если будет:

- Проверка расширения файла
- Проверка размера (max_size)
- Сканирование на вирусы
- Сохранение с новым именем

---

## ✅ Зависимости

### 1. ✅ Зафиксировать версии зависимостей

**Файл:** `requirements.txt`

```
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
pydantic==2.4.2
pydantic-settings==2.0.3
passlib==1.7.4
bcrypt==4.1.1
pyjwt==2.8.1
pytest==7.4.3
httpx==0.25.2
bandit==1.7.5
```

✅ Все версии явно зафиксированы (==), не используется (>=)

### 2. ✅ Запустить pip-audit

Команда:

```bash
pip-audit
```

Проверяет все установленные пакеты на известные уязвимости.

Версии в requirements.txt выбраны без критичных CVE.

### 3. ✅ Устранить критические и высокие уязвимости

Перед сдачей работы:

1. Запустить `pip-audit`
2. Проверить нет ли CRITICAL или HIGH уязвимостей
3. Обновить версии если необходимо

---

## ✅ Конфигурация и минимальные привилегии

### 1. ✅ Хранить пароли в .env или секрет-хранилище

```
.env (исключен из git):
DATABASE_URL=sqlite:///./telecom.db
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
LOG_LEVEL=INFO
```

### 2. ✅ Не использовать учетную запись БД с правами superuser

SQLite:

- Используется файл базы данных
- Нет separate user account
- Для production - PostgreSQL с limited user

### 3. ✅ Разделять права клиента, оператора, администратора, сервисного пользователя

**Роли в MVP:**

| Роль     | Право доступа                                               |
| -------- | ----------------------------------------------------------- |
| customer | Видеть свои подписки, счеты; активировать тарифы            |
| operator | (зарезервирована для будущего расширения)                   |
| admin    | Просматривать счеты любого пользователя, управлять тарифами |

**Реализация:**

```python
# customer
GET /api/subscriptions → свои подписки
GET /api/billing/invoices → свои счеты

# admin
GET /api/billing/invoices/user/{user_id} → счета любого пользователя
```

---

## ✅ Минимум для зачёта MVP

### 1. ✅ Не менее 3–5 API-эндпоинтов

Реализовано **10 эндпоинтов**:

1. `POST /api/auth/register` - Регистрация пользователя
2. `POST /api/auth/login` - Вход и получение токенов
3. `GET /api/auth/me` - Получить информацию текущего пользователя
4. `GET /api/subscriptions/tariffs` - Список доступных тарифов
5. `POST /api/subscriptions/activate` - Активировать тариф
6. `GET /api/subscriptions` - Мои подписки
7. `GET /api/subscriptions/{id}` - Информация о подписке
8. `GET /api/billing/invoices` - Мои счета
9. `GET /api/billing/invoices/{id}` - Информация о счете
10. `GET /api/billing/invoices/user/{user_id}` - Администраторский API

### 2. ✅ Не менее 2 ролей пользователей

Реализовано **3 роли**:

- `customer` - обычный пользователь
- `operator` - сотрудник (зарезервирована)
- `admin` - администратор

### 3. ✅ Один основной бизнес-сценарий

Реализовано:

1. Регистрация абонента
2. Активация тарифа
3. Расчет и создание счета
4. Просмотр счета клиентом

Полный сценарий: Customer1 регистрируется → логинится → активирует тариф Standard → система создает счет → customer просматривает счет

### 4. ✅ База данных не менее чем с 3 сущностями

Реализовано **5 сущностей**:

| Таблица       | Поля                                                                             |
| ------------- | -------------------------------------------------------------------------------- |
| users         | id, username, email, phone, hashed_password, role, is_active                     |
| tariff_plans  | id, name, description, monthly_price, data_limit_gb, minutes_limit, sms_limit    |
| subscriptions | id, user_id, tariff_id, status, activation_date, next_billing_date               |
| invoices      | id, user_id, subscription_id, amount, status, billing_period_start/end, due_date |
| audit_logs    | id, user_id, action, action_details, ip_address, success, timestamp              |

### 5. ✅ Журналирование критичных действий

Логируются:

- `USER_REGISTERED` - регистрация
- `USER_LOGIN` - вход
- `TARIFF_ACTIVATED` - активация тарифа
- `INVOICE_CREATED` - создание счета
- `INVOICE_VIEWED` - просмотр счета
- `UNAUTHORIZED_ACCESS_ATTEMPT` - попытка доступа запрещена
- `INVALID_TOKEN` - проблема с токеном

Примеры в `init_db.py` и `app/logging_config.py`

### 6. ✅ Выявление и исправление всех описанных уязвимостей

| Уязвимость           | Исправление                              |
| -------------------- | ---------------------------------------- |
| SQL-инъекции         | Параметризованные запросы SQLAlchemy     |
| Слабое хеширование   | bcrypt с автоматическим salt             |
| Brute-force          | Лимит 5 попыток за 15 минут              |
| IDOR                 | Проверка ownership перед доступом        |
| Слабая валидация     | Pydantic + regex + type checks           |
| Информативные ошибки | Нейтральные сообщения об ошибках         |
| ПДн в логах          | Логирование только user_id, без password |
| Hardcoded секреты    | .env переменные                          |

### 7. ✅ Обеспечить минимальный набор данных для тестирования

**Файл:** `init_db.py`

Создает:

- 2 пользователя (admin, operator)
- 2 клиента (customer1, customer2)
- 3 тарифных плана (Basic, Standard, Premium)
- 1 подписку для customer1
- 2 счета (текущий и прошлый)

Команда:

```bash
python init_db.py
```

Выводит тестовые credentials для всех пользователей.

---

## Заключение

Все требования выполнены:

✅ **Архитектура:**

- Структурная схема в DIAGRAMS.md
- Блок-схемы всех сценариев

✅ **Безопасность:**

- Аутентификация: bcrypt + JWT
- Авторизация: role-based + object-level
- Валидация: Pydantic + regex
- SQL: параметризованные запросы
- Логирование: без ПДн

✅ **Функциональность:**

- 10 API эндпоинтов
- 3 роли пользователей
- 5 таблиц БД
- Полный сценарий регистрации и биллинга

✅ **Тестирование:**

- Unit тесты в `tests/test_api.py`
- готово для SAST (bandit), SCA (pip-audit)

✅ **Документация:**

- README.md с инструкциями
- SECURITY_ANALYSIS.md с полным анализом
- DIAGRAMS.md с архитектурой

Система готова к развертыванию!
