# Задание 2. Контрольные списки для проверки кода безопасности

## Тема и вариант

- Тема: безопасная разработка и проверка MVP
- Вариант: 6, телекоммуникации
- Проект: регистрация абонентов, предоплатная активация тарифа, выставление и просмотр счетов

---

## 1. Входные данные

### Контрольный список

| Проверка | Что требуется | Реализация в проекте | Подтверждение | Статус |
|---|---|---|---|---|
| Наличие обязательных полей | Проверить, что обязательные поля не могут быть пропущены | Pydantic требует обязательные поля в запросах | [app/schemas.py](/Users/tsarevich/web/telecom/app/schemas.py:6) | Выполнено |
| Проверка типа | Строки, числа, email, path params должны иметь явный тип | Все request/response схемы и path params типизированы | [app/schemas.py](/Users/tsarevich/web/telecom/app/schemas.py:6), [app/routers/invoices.py](/Users/tsarevich/web/telecom/app/routers/invoices.py:43) | Выполнено |
| Проверка формата | Email, username, phone, password pattern | Используются `EmailStr`, regex и custom validators | [app/schemas.py](/Users/tsarevich/web/telecom/app/schemas.py:12) | Выполнено |
| Проверка диапазона | `tariff_id > 0`, корректные значения ID | Для активации тарифа задано `gt=0` | [app/schemas.py](/Users/tsarevich/web/telecom/app/schemas.py:106) | Выполнено |
| Проверка длины | Ограничение длины username, phone, password | Через `min_length`, `max_length` | [app/schemas.py](/Users/tsarevich/web/telecom/app/schemas.py:8) | Выполнено |
| Допустимые значения | Статусы и роли контролируются серверной логикой | Роли проверяются в dependencies, статусы выставляются из кода, а не из пользовательского ввода | [app/dependencies.py](/Users/tsarevich/web/telecom/app/dependencies.py:54), [app/routers/subscriptions.py](/Users/tsarevich/web/telecom/app/routers/subscriptions.py:85) | Выполнено |
| Защита от инъекций | Не подставлять пользовательский ввод в SQL | Используются ORM-запросы SQLAlchemy | [app/routers/auth.py](/Users/tsarevich/web/telecom/app/routers/auth.py:70), [app/routers/invoices.py](/Users/tsarevich/web/telecom/app/routers/invoices.py:62) | Выполнено |

### Примеры кода

```python
username: str = Field(..., min_length=3, max_length=50)
email: EmailStr
phone: str = Field(..., min_length=10, max_length=20)
password: str = Field(..., min_length=8, max_length=128)
```

Источник: [app/schemas.py](/Users/tsarevich/web/telecom/app/schemas.py:8)

```python
tariff_id: int = Field(..., gt=0)
```

Источник: [app/schemas.py](/Users/tsarevich/web/telecom/app/schemas.py:106)

### Вывод по разделу

Входные данные валидируются корректно по типу, длине, формату и диапазону. Основной оставшийся риск не в валидации, а в необходимости расширить автоматические тесты на все ветки ошибок.

---

## 2. Аутентификация

### Контрольный список

| Проверка | Что требуется | Реализация в проекте | Подтверждение | Статус |
|---|---|---|---|---|
| Хранение паролей в виде хеша | Пароль не хранится в открытом виде | Используется `bcrypt` через `passlib` | [app/security.py](/Users/tsarevich/web/telecom/app/security.py:7) | Выполнено |
| Проверка пароля | Сравнение с хешем, а не с plain text | `verify_password()` | [app/security.py](/Users/tsarevich/web/telecom/app/security.py:16) | Выполнено |
| Access token | Должен иметь ограниченный срок жизни | TTL через `access_token_expire_minutes` | [app/security.py](/Users/tsarevich/web/telecom/app/security.py:21) | Выполнено |
| Refresh token | Должен быть отдельным и ограниченным по сроку | Отдельный `create_refresh_token()` и `type="refresh"` | [app/security.py](/Users/tsarevich/web/telecom/app/security.py:43) | Выполнено |
| Защита Bearer flow | Токен должен читаться из `Authorization` header | Используется `HTTPBearer` | [app/dependencies.py](/Users/tsarevich/web/telecom/app/dependencies.py:11) | Выполнено |
| Refresh endpoint | Должен существовать | `POST /api/auth/refresh` реализован | [app/routers/auth.py](/Users/tsarevich/web/telecom/app/routers/auth.py:214) | Выполнено |
| Logout | Должен существовать | `POST /api/auth/logout` реализован | [app/routers/auth.py](/Users/tsarevich/web/telecom/app/routers/auth.py:276) | Выполнено |
| Ограничение попыток входа | Базовая защита от brute-force | In-memory lockout на 5 попыток / 15 минут | [app/routers/auth.py](/Users/tsarevich/web/telecom/app/routers/auth.py:18) | Частично выполнено |

### Примеры кода

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

Источник: [app/security.py](/Users/tsarevich/web/telecom/app/security.py:8)

```python
bearer_scheme = HTTPBearer(auto_error=False)
```

Источник: [app/dependencies.py](/Users/tsarevich/web/telecom/app/dependencies.py:11)

```python
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 900
```

Источник: [app/routers/auth.py](/Users/tsarevich/web/telecom/app/routers/auth.py:20)

### Вывод по разделу

Аутентификация реализована на хорошем уровне для MVP. Слабое место — rate limiting хранится в памяти процесса, поэтому не подходит для нескольких инстансов приложения и теряется после рестарта.

---

## 3. Авторизация

### Контрольный список

| Проверка | Что требуется | Реализация в проекте | Подтверждение | Статус |
|---|---|---|---|---|
| Права на серверной стороне | Нельзя доверять клиенту | Проверки ролей реализованы в dependencies и роутерах | [app/dependencies.py](/Users/tsarevich/web/telecom/app/dependencies.py:54) | Выполнено |
| Доступ к конкретному объекту | Клиент должен видеть только свой счет/подписку | Проверки `invoice.user_id == current_user.id` и аналогично для подписок | [app/routers/invoices.py](/Users/tsarevich/web/telecom/app/routers/invoices.py:72), [app/routers/subscriptions.py](/Users/tsarevich/web/telecom/app/routers/subscriptions.py:169) | Выполнено |
| Изоляция административных функций | Оператор и админ имеют отдельный read-only доступ, клиент — нет | Используется `get_current_operator()` и условные проверки ролей | [app/dependencies.py](/Users/tsarevich/web/telecom/app/dependencies.py:67) | Выполнено |
| Защита от повышения привилегий | Роль нельзя задать из запроса регистрации | Роль пользователя при регистрации принудительно задаётся как `customer` | [app/routers/auth.py](/Users/tsarevich/web/telecom/app/routers/auth.py:105) | Выполнено |
| Изоляция внутреннего billing API | Служебные операции не должны вызываться клиентским JWT | Есть отдельный internal endpoint с `X-Internal-API-Key` | [app/dependencies.py](/Users/tsarevich/web/telecom/app/dependencies.py:96), [app/routers/internal_billing.py](/Users/tsarevich/web/telecom/app/routers/internal_billing.py:16) | Выполнено |

### Примеры кода

```python
if invoice.user_id != current_user.id and current_user.role not in ["operator", "admin"]:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Доступ запрещен"
    )
```

Источник: [app/routers/invoices.py](/Users/tsarevich/web/telecom/app/routers/invoices.py:72)

```python
new_user = User(
    username=user_data.username,
    email=user_data.email,
    phone=user_data.phone,
    hashed_password=hashed_password,
    role="customer"
)
```

Источник: [app/routers/auth.py](/Users/tsarevich/web/telecom/app/routers/auth.py:105)

### Вывод по разделу

Авторизация реализована корректно для учебного MVP: сервер сам принимает решения о доступе, клиент не может повысить привилегии, а доступ к счетам и подпискам ограничен владельцем или служебной ролью.

---

## 4. Данные и логирование

### Контрольный список

| Проверка | Что требуется | Реализация в проекте | Подтверждение | Статус |
|---|---|---|---|---|
| Нет лишних полей в API | Не возвращать password/hash и лишние ПДн | Используются response-модели `UserResponse`, `InvoiceResponse`, `SubscriptionResponse` | [app/schemas.py](/Users/tsarevich/web/telecom/app/schemas.py:61), [app/schemas.py](/Users/tsarevich/web/telecom/app/schemas.py:92) | Выполнено |
| Нет паролей и токенов в логах | Запрет на логирование чувствительных данных | Это явно зафиксировано в `log_audit()` | [app/logging_config.py](/Users/tsarevich/web/telecom/app/logging_config.py:61) | Выполнено |
| Нейтральные сообщения об ошибках | Не раскрывать внутренние детали в auth и DB errors | Используются нейтральные `401`, `403`, `500` | [app/main.py](/Users/tsarevich/web/telecom/app/main.py:41), [app/routers/auth.py](/Users/tsarevich/web/telecom/app/routers/auth.py:169) | Выполнено |
| Аудит критичных действий | Должен существовать audit trail | Критичные действия сохраняются в `audit_logs` | [app/logging_config.py](/Users/tsarevich/web/telecom/app/logging_config.py:28) | Выполнено |
| Логирование security events | Попытки нарушений должны фиксироваться | `log_security_event()` сохраняет события в БД и в стандартный лог | [app/logging_config.py](/Users/tsarevich/web/telecom/app/logging_config.py:91) | Выполнено |

### Примеры кода

```python
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
```

Источник: [app/schemas.py](/Users/tsarevich/web/telecom/app/schemas.py:92)

```python
_persist_audit_record(
    action=action.value,
    user_id=user_id,
    details=details,
    ip_address=ip_address,
    success=success
)
```

Источник: [app/logging_config.py](/Users/tsarevich/web/telecom/app/logging_config.py:81)

### Вывод по разделу

Логирование реализовано правильно для учебной задачи: данные не переэкспонируются через API, чувствительные значения не должны попадать в логи, а аудит ведется как в консоль, так и в БД.

---

## 5. Криптография

### Контрольный список

| Проверка | Что требуется | Реализация в проекте | Подтверждение | Статус |
|---|---|---|---|---|
| Современные алгоритмы для паролей | Использовать bcrypt/Argon2/PBKDF2 | Используется `bcrypt` через `passlib` | [app/security.py](/Users/tsarevich/web/telecom/app/security.py:8) | Выполнено |
| Нет самописной криптографии | Использовать библиотечные решения | Хеширование и JWT реализованы через стандартные библиотеки | [app/security.py](/Users/tsarevich/web/telecom/app/security.py:1) | Выполнено |
| Подписанные токены | JWT подписываются по `HS256` | `jwt.encode(..., settings.secret_key, algorithm=settings.algorithm)` | [app/security.py](/Users/tsarevich/web/telecom/app/security.py:33) | Выполнено |
| Ограниченный срок жизни токена | Нельзя использовать бессрочные токены | `exp` задаётся для access и refresh | [app/security.py](/Users/tsarevich/web/telecom/app/security.py:28), [app/security.py](/Users/tsarevich/web/telecom/app/security.py:47) | Выполнено |
| Нет захардкоженных рабочих секретов | Секреты должны быть во внешней конфигурации | Используются `.env` и `BaseSettings`, но в коде остаются небезопасные дефолты | [app/config.py](/Users/tsarevich/web/telecom/app/config.py:5) | Частично выполнено |

### Вывод по разделу

Криптография реализована приемлемо: используется bcrypt и JWT с ограниченным TTL. Основной остаточный риск — наличие insecure defaults в конфигурации, которые нужно убрать до финальной сдачи.

---

## 6. Зависимости и базовая безопасность окружения разработки

### 6.1. Проверка версий библиотек

Основные зафиксированные зависимости:

- `fastapi==0.104.1`
- `sqlalchemy==2.0.23`
- `psycopg2-binary==2.9.9`
- `pydantic==2.4.2`
- `passlib==1.7.4`
- `bcrypt==4.1.1`
- `pyjwt==2.12.1`
- `pip-audit==2.6.1`
- `bandit==1.7.5`

Источник: [requirements.txt](/Users/tsarevich/web/telecom/requirements.txt:1)

### 6.2. Проверка хранения секретов в репозитории

| Проверка | Результат | Подтверждение | Статус |
|---|---|---|---|
| `.env` исключён из Git | Да | [.gitignore](/Users/tsarevich/web/telecom/.gitignore:1) | Выполнено |
| `.env.example` используется как шаблон | Да | [.env.example](/Users/tsarevich/web/telecom/.env.example:1) | Выполнено |
| В коде нет необходимости хранить реальные секреты | Частично | В коде всё ещё есть небезопасные default values | [app/config.py](/Users/tsarevich/web/telecom/app/config.py:5) | Частично выполнено |

### 6.3. Результат SAST

Плановый инструмент: `bandit -r app/`

Фактический статус проверки в текущем окружении:

- для запуска был установлен недостающий пакет `pbr`;
- после этого `bandit` был успешно выполнен по каталогу `app/`;
- инструмент завершился с находками, то есть SAST-отчёт получен.

Краткий результат `bandit`:

```text
Total issues:
- Low: 2
- Medium: 1
- High: 0
```

Найденные проблемы:

1. `B105:hardcoded_password_string` в [app/logging_config.py](/Users/tsarevich/web/telecom/app/logging_config.py:28)  
   `INVALID_TOKEN = "invalid_token"`  
   Комментарий: вероятнее всего ложноположительное срабатывание по слову `token`.

2. `B105:hardcoded_password_string` в [app/logging_config.py](/Users/tsarevich/web/telecom/app/logging_config.py:29)  
   `PASSWORD_CHANGED = "password_changed"`  
   Комментарий: вероятнее всего ложноположительное срабатывание по слову `password`.

3. `B104:hardcoded_bind_all_interfaces` в [app/main.py](/Users/tsarevich/web/telecom/app/main.py:103)  
   `uvicorn.run(app, host="0.0.0.0", port=8000)`  
   Комментарий: допустимо для локальной разработки, но для production требует более осторожной конфигурации.

### 6.4. Результат SCA

Плановый инструмент: `pip-audit`

Фактический статус проверки в текущем окружении:

- `pip-audit` был успешно выполнен с доступом к online vulnerability feed;
- инструмент завершился с отчётом об уязвимостях в зависимостях;
- SCA-результат получен.

Краткий результат `pip-audit`:

```text
Found 12 known vulnerabilities in 5 packages
```

Найденные уязвимые зависимости:

| Пакет | Версия | Идентификатор | Исправление |
|---|---|---|---|
| `fastapi` | `0.104.1` | `PYSEC-2024-38` | `0.109.1` |
| `pip` | `24.2` | `GHSA-4xh5-x5gv-qwph` | `25.3` |
| `pip` | `24.2` | `GHSA-6vgw-5pg2-w6jp` | `26.0` |
| `pip` | `24.2` | `ECHO-ffe1-1d3c-d9bc` | `25.2+echo.1` |
| `pip` | `24.2` | `ECHO-7db2-03aa-5591` | `25.2+echo.1` |
| `pytest` | `7.4.3` | `GHSA-6w46-j5rx-g56g` | `9.0.3` |
| `python-multipart` | `0.0.6` | `GHSA-2jv5-9r88-3w3p` | `0.0.7` |
| `python-multipart` | `0.0.6` | `GHSA-59g5-xgcq-4qw3` | `0.0.18` |
| `python-multipart` | `0.0.6` | `GHSA-wp53-j4wj-2cfg` | `0.0.22` |
| `python-multipart` | `0.0.6` | `GHSA-mj87-hwqh-73pj` | `0.0.26` |
| `starlette` | `0.27.0` | `GHSA-f96h-pmfr-66vw` | `0.40.0` |
| `starlette` | `0.27.0` | `GHSA-2c2j-9gv5-cj73` | `0.47.2` |

### 6.5. Вывод по разделу

Зависимости в проекте зафиксированы, `.env` исключён из Git, а проверки `bandit` и `pip-audit` теперь успешно воспроизведены с реальными результатами. По итогам SAST критических и high-issues не обнаружено, однако есть 1 medium и 2 low finding'а, требующие анализа и, при необходимости, уточнения конфигурации. По итогам SCA обнаружено 12 известных уязвимостей в 5 пакетах, поэтому перед финальной сдачей рекомендуется обновить как минимум `fastapi`, `starlette`, `python-multipart` и `pytest`, а также обновить `pip` в окружении разработки.

---

## Таблица рисков, предотвращённых в MVP

| Риск | Механизм защиты | Где реализовано | Статус |
|---|---|---|---|
| SQL injection | ORM-запросы SQLAlchemy | [app/routers/auth.py](/Users/tsarevich/web/telecom/app/routers/auth.py:70), [app/routers/invoices.py](/Users/tsarevich/web/telecom/app/routers/invoices.py:62) | Предотвращён |
| Слабое хранение паролей | bcrypt + passlib | [app/security.py](/Users/tsarevich/web/telecom/app/security.py:8) | Предотвращён |
| Использование бессрочного токена | `exp` в access/refresh JWT | [app/security.py](/Users/tsarevich/web/telecom/app/security.py:28) | Предотвращён |
| IDOR для счетов | Object-level access check | [app/routers/invoices.py](/Users/tsarevich/web/telecom/app/routers/invoices.py:72) | Предотвращён |
| Повышение привилегий через регистрацию | Роль задаётся сервером как `customer` | [app/routers/auth.py](/Users/tsarevich/web/telecom/app/routers/auth.py:105) | Предотвращён |
| Утечка ПДн через invoice API | Отдельные response-модели без лишних полей | [app/schemas.py](/Users/tsarevich/web/telecom/app/schemas.py:92) | Предотвращён |
| Отсутствие аудита | `audit_logs` + системное логирование | [app/logging_config.py](/Users/tsarevich/web/telecom/app/logging_config.py:28) | Предотвращён |
| Неоплаченный тариф остаётся активным | Предоплатная модель `pending_payment -> paid -> active` | [app/routers/subscriptions.py](/Users/tsarevich/web/telecom/app/routers/subscriptions.py:85), [app/routers/invoices.py](/Users/tsarevich/web/telecom/app/routers/invoices.py:192) | Предотвращён |
| Несанкционированный вызов внутренних billing-операций | Отдельный internal endpoint + `X-Internal-API-Key` | [app/dependencies.py](/Users/tsarevich/web/telecom/app/dependencies.py:96), [app/routers/internal_billing.py](/Users/tsarevich/web/telecom/app/routers/internal_billing.py:16) | Предотвращён |

---

## Итог по заданию 2

Контрольные списки по входным данным, аутентификации, авторизации, логированию и криптографии в основном закрыты. Наиболее заметные остаточные проблемы:

- небезопасные default values в конфигурации;
- import-time инициализация БД в `app/main.py`;
- невоспроизведённые в текущем окружении автоматические отчёты `bandit` и `pip-audit`.

Для финальной сдачи рекомендуется:

1. убрать небезопасные default values из [app/config.py](/Users/tsarevich/web/telecom/app/config.py:1);
2. вынести создание таблиц из import-time в отдельную инициализацию;
3. повторно выполнить `bandit` и `pip-audit` в рабочем окружении и приложить результаты в отчёт.
