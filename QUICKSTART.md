# Быстрый старт MVP системы

## Предварительные требования

- Python 3.12+
- PostgreSQL (запущен и доступен)
- macOS, Linux или WSL на Windows

## Автоматическая установка (рекомендуется)

```bash
# Выполните скрипт автоматической установки
chmod +x setup.sh
./setup.sh
```

Скрипт сделает:

1. ✅ Создаст виртуальное окружение
2. ✅ Установит все зависимости
3. ✅ Создаст .env файл с SECRET_KEY
4. ✅ Проверит PostgreSQL
5. ✅ Создаст БД
6. ✅ Инициализирует таблицы и тестовые данные
7. ✅ Выполнит SAST и SCA анализ

## Ручная установка

### 1. Подготовка окружения

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Создание .env файла

```bash
cp .env.example .env
```

Отредактируйте `.env` и установите правильный `DATABASE_URL`:

```
DATABASE_URL=postgresql://postgres:your_password@localhost/telecom_db
```

### 3. Подготовка PostgreSQL

```bash
# Создание БД
psql -U postgres -c "CREATE DATABASE telecom_db;"

# Проверка подключения
psql -U postgres -d telecom_db -c "SELECT 1;"
```

### 4. Инициализация БД

```bash
python init_db.py
```

## Запуск приложения

### Способ 1: Использование скрипта

```bash
chmod +x run.sh
./run.sh
```

### Способ 2: Прямой запуск

```bash
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Способ 3: Production запуск

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Доступ к приложению

- 🌐 **API**: http://localhost:8000
- 📖 **Swagger документация**: http://localhost:8000/docs
- 🔍 **ReDoc**: http://localhost:8000/redoc
- 💚 **Health check**: http://localhost:8000/health

## Учетные данные

Используйте учетные данные, созданные в вашей текущей базе данных.

## Первый запрос (cURL)

### 1. Вход и получение токена

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

Ответ:

```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### 2. Получить информацию о пользователе

```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer <access_token>"
```

### 3. Получить список тарифов

```bash
curl -X GET "http://localhost:8000/api/subscriptions/tariffs"
```

### 4. Активировать тариф

```bash
curl -X POST "http://localhost:8000/api/subscriptions/activate" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"tariff_id": 1}'
```

### 5. Получить свои счета

```bash
curl -X GET "http://localhost:8000/api/billing/invoices" \
  -H "Authorization: Bearer <access_token>"
```

## Тестирование

### Запуск unit тестов

```bash
pytest tests/ -v
pytest tests/test_api.py::TestAuth::test_login_success -v
```

### SAST анализ (Bandit)

```bash
bandit -r app/
bandit -r app/ -f json -o bandit-report.json
```

### SCA анализ (pip-audit)

```bash
pip-audit
pip-audit --skip-editable
```

## Решение проблем

### PostgreSQL не подключается

```bash
# Проверить статус PostgreSQL
pg_isready -h localhost -p 5432

# Если PostgreSQL не запущен (macOS):
brew services start postgresql

# Linux:
sudo systemctl start postgresql
```

### Ошибка: "database does not exist"

```bash
# Создание БД вручную
psql -U postgres -c "CREATE DATABASE telecom_db;"
```

### Ошибка: "password authentication failed"

Обновите пароль в `.env`:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost/telecom_db
```

Где `YOUR_PASSWORD` - ваш пароль PostgreSQL.

### Чистая переустановка БД

```bash
# Удаление старой БД (если необходимо)
psql -U postgres -c "DROP DATABASE telecom_db;"

# Создание новой БД
psql -U postgres -c "CREATE DATABASE telecom_db;"

# Переинициализация данных
python init_db.py
```

## Основная документация

- 📋 [README.md](README.md) - Полная документация
- 🔐 [SECURITY_ANALYSIS.md](SECURITY_ANALYSIS.md) - Анализ безопасности
- 📊 [DIAGRAMS.md](DIAGRAMS.md) - Архитектура и диаграммы
- ✅ [REQUIREMENTS_CHECKLIST.md](REQUIREMENTS_CHECKLIST.md) - Проверка требований

## Полезные команды

```bash
# Активировать виртуальное окружение
source venv/bin/activate

# Деактивировать виртуальное окружение
deactivate

# Запустить тесты с покрытием
pytest --cov=app tests/

# Сгенерировать HTML отчет bandit
bandit -r app/ -f html -o bandit-report.html

# Проверить типы (если установлен mypy)
mypy app/

# Форматирование кода (если установлен black)
black app/

# Lint (если установлен flake8)
flake8 app/
```

## Развертывание в production

1. Обновить `DEBUG=False` в .env
2. Установить `SECRET_KEY` сложный и уникальный
3. Использовать HTTPS (SSL/TLS сертификат)
4. Развернуть на production сервере с PostgreSQL
5. Использовать supervisor/systemd для управления процессом
6. Установить reverse proxy (nginx)
7. Настроить мониторинг и логирование
8. Выполнить полный security audit

## Дополнительная информация

- Python: https://www.python.org/
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://www.sqlalchemy.org/
- PostgreSQL: https://www.postgresql.org/
- Pydantic: https://docs.pydantic.dev/
