# Telecom Secure MVP

Практическая работа №6: разработка и оценка защищенности MVP-продукта по принципам Secure SDLC и OWASP Top 10.

## Тема, цель, вариант

- Тема: разработка и аудит защищенного MVP телеком-провайдера.
- Цель: реализовать прикладную систему с ролями, аутентификацией, биллингом, журналированием и анализом защищенности.
- Вариант: телекоммуникационная платформа регистрации клиентов, подключения тарифов и выставления счетов.

## Краткое описание MVP

Проект представляет собой клиент-серверную систему для обслуживания абонентов. Пользователь может зарегистрироваться, войти в систему, выбрать тариф, активировать подписку в режиме предоплаты, получить счет и оплатить его. Оператор или администратор могут просматривать клиентские подписки и счета в пределах прав доступа.

Состав проекта:

- Backend: `FastAPI` + `SQLAlchemy` + `JWT` + аудит безопасности.
- Frontend: `React` + `Vite` с современным адаптивным интерфейсом.
- Хранение данных: PostgreSQL или SQLite для тестов.
- Тестирование: `pytest`, проверки бизнес-логики и контролей безопасности.

## Архитектура системы

1. React SPA в каталоге [frontend](/Users/tsarevich/web/telecom/frontend) работает как пользовательский интерфейс.
2. FastAPI API в [app/main.py](/Users/tsarevich/web/telecom/app/main.py) обслуживает аутентификацию, подписки, биллинг и внутренние сервисные операции.
3. Слой доступа к данным на `SQLAlchemy` использует сущности `User`, `TariffPlan`, `Subscription`, `Invoice`, `AuditLog`.
4. Компонент безопасности включает валидацию входных данных, JWT access/refresh токены, хеширование паролей, RBAC и аудит.

## Роли пользователей и разграничение доступа

- `customer`: регистрация, вход, просмотр собственных тарифов, подписок и счетов, оплата собственных счетов.
- `operator`: все возможности клиента плюс просмотр подписок и счетов других пользователей через операторские endpoint’ы.
- `admin`: полный доступ оператора и расширенный административный контроль.

Контроль доступа реализован в [app/dependencies.py](/Users/tsarevich/web/telecom/app/dependencies.py) через `get_current_user`, `get_current_operator`, `ensure_subscription_access`, `ensure_invoice_access`.

## Основной бизнес-сценарий

1. Пользователь регистрируется.
2. Пользователь проходит аутентификацию и получает `access_token` и `refresh_token`.
3. Пользователь выбирает тариф из списка активных.
4. Backend создает подписку в статусе `pending_payment` и формирует счет.
5. Пользователь оплачивает счет.
6. Backend переводит подписку в статус `active`, фиксирует событие в журнале аудита.

## Реализованный фронтенд

Фронтенд находится в [frontend/src/App.jsx](/Users/tsarevich/web/telecom/frontend/src/App.jsx) и включает:

- экран входа и регистрации с клиентской валидацией;
- защищенное хранение токенов в `sessionStorage`;
- автоматическое обновление access token через refresh token;
- дашборд с обзором состояния аккаунта;
- раздел тарифов с активацией;
- раздел подписок;
- биллинг со списком счетов, оплатой и экспортом CSV/JSON;
- раздел безопасности с отображением реализованных защитных механизмов;
- операторскую панель для ролей `operator` и `admin`.

## Минимальные требования задания

- Пользовательский интерфейс: реализован на React + Vite.
- Не менее 5 API-эндпоинтов: реализовано более 10 endpoint’ов.
- Не менее 3 сущностей БД: `User`, `TariffPlan`, `Subscription`, `Invoice`, `AuditLog`.
- Не менее 2 ролей: `customer`, `operator`, `admin`.
- Основной функциональный сценарий: реализован полностью.
- Проверка входных данных: `Pydantic` и клиентская валидация.
- Защита паролей: `bcrypt/passlib`.
- Разграничение доступа: RBAC и owner-based authorization.
- Журналирование критичных действий: реализовано через audit/security logging.

## Реализованные механизмы безопасности

- Хеширование паролей в [app/security.py](/Users/tsarevich/web/telecom/app/security.py).
- JWT-токены с `type`, `iat`, `exp`, `jti`, `refresh token rotation`.
- Ограничение частоты brute-force попыток входа в [app/routers/auth.py](/Users/tsarevich/web/telecom/app/routers/auth.py).
- Ограничение размера HTTP body в [app/main.py](/Users/tsarevich/web/telecom/app/main.py).
- Валидация username, phone, password и безопасная нормализация input.
- Проверка прав доступа к счетам и подпискам.
- Санитизация экспортируемых CSV-данных и имен файлов.
- Безопасное хранение секретов через `.env`.
- Безопасное журналирование без утечки паролей, токенов и SQL-ошибок наружу.

## Анализ по OWASP Top 10

| Категория риска | Место обнаружения | Описание проблемы | Возможные последствия | Критичность | Исправление |
|---|---|---|---|---|---|
| Broken Access Control | `subscriptions`, `invoices` | Риск доступа к чужим счетам или подпискам по ID | Утечка данных, несанкционированные операции | Высокая | Реализованы `ensure_subscription_access` и `ensure_invoice_access` |
| Authentication Failures | `auth/login`, `auth/refresh` | Риск перебора паролей и повторного использования refresh token | Захват учетной записи | Высокая | Lockout после серии ошибок, rotation refresh token |
| Injection | ORM-запросы, экспорт CSV | Риск SQL/CSV injection при небезопасной обработке данных | Выполнение нежелательных команд, порча данных | Средняя | SQLAlchemy ORM, входная валидация, `csv_sanitize_cell` |
| Security Misconfiguration | `config`, запуск | Риск хранения секретов в коде | Компрометация системы | Высокая | Секреты вынесены в `.env`, подготовлен `.env.example` |
| Cryptographic Failures | `security.py` | Риск хранения паролей в открытом виде или слабой подписи | Компрометация учетных данных | Высокая | `bcrypt`, JWT с секретным ключом и проверкой подписи |
| Insecure Design | сценарий доступа к ресурсам | Риск отсутствия role/owner checks | Нарушение бизнес-ограничений | Высокая | Role-based и object-based authorization |
| Software or Data Integrity Failures | refresh flow, export | Риск использования неподписанных или устаревших токенов | Подмена сессии, нарушение целостности | Средняя | Верификация JWT, versioned refresh token |
| Security Logging and Alerting Failures | `logging_config.py` | Риск отсутствия аудита значимых событий | Позднее обнаружение атак | Средняя | Аудит входа, отказов, оплат, доступа, внутренних ошибок |
| Mishandling of Exceptional Conditions | `main.py` | Риск утечки SQL stack traces и внутренних ошибок | Разведка приложения злоумышленником | Средняя | Единые 4xx/5xx обработчики с безопасными сообщениями |
| Software Supply Chain Failures | `requirements.txt`, `package.json` | Риск уязвимых зависимостей | Удаленное выполнение кода, утечка данных | Средняя | Версионирование зависимостей, рекомендуется `pip-audit` и `npm audit` |

## Результаты повторного тестирования

Проверки backend:

- регистрация и вход;
- валидация username, phone и password;
- запрет доступа refresh token к защищенным endpoint’ам;
- rotation refresh token;
- запрет доступа клиента к чужим счетам и подпискам;
- ограничение `limit`;
- защита от oversized request body;
- экспорт CSV и JSON.

Команда запуска тестов backend:

```bash
pytest
```

Команды для frontend:

```bash
cd frontend
npm install
npm run dev
```

Backend запускается отдельно:

```bash
uvicorn app.main:app --reload
```

## Перечень технологий

- Python 3
- FastAPI
- SQLAlchemy
- PostgreSQL / SQLite
- Passlib + bcrypt
- Python-JOSE
- React 18
- Vite 5
- CSS3
- Pytest

## Секреты и конфигурация

Все секреты и параметры подключения должны находиться вне исходного кода:

- `DATABASE_URL`
- `SECRET_KEY`
- `INTERNAL_API_KEY`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`

Пример приведен в [.env.example](/Users/tsarevich/web/telecom/.env.example) и [frontend/.env.example](/Users/tsarevich/web/telecom/frontend/.env.example).

## Вывод

В проекте реализован завершенный MVP с пользовательским интерфейсом, серверной логикой, хранением данных, ролями пользователей и базовыми механизмами защищенной разработки. Система покрывает основной бизнес-сценарий варианта и демонстрирует практическое применение Secure SDLC и OWASP Top 10 при разработке прикладного продукта.
