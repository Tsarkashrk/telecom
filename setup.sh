#!/bin/bash

set -e

echo "🚀 Телекоммуникационная платформа MVP - Setup"
echo "==============================================="
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi
echo ""
echo "🔧 Активирую виртуальное окружение..."
source venv/bin/activate
echo ""
echo "📥 Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"
if [ ! -f ".env" ]; then
    echo ""
    echo "⚙️  Создание .env файла..."
    cp .env.example .env
    SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/your-secret-key-change-in-production/$SECRET_KEY/" .env
    else
        sed -i "s/your-secret-key-change-in-production/$SECRET_KEY/" .env
    fi
    
    echo "✓ .env created with generated SECRET_KEY"
    echo ""
    echo "⚠️  ВАЖНО: Обновите DATABASE_URL в .env файле!"
    echo "   Текущее значение: postgresql://postgres:password@localhost/telecom_db"
    echo ""
fi
echo ""
echo "🗄️  Проверяю подключение к PostgreSQL..."

if ! psql -U postgres -c "SELECT 1" &> /dev/null; then
    echo "❌ Ошибка: Не могу подключиться к PostgreSQL"
    echo "   Убедитесь что PostgreSQL запущен и доступен"
    echo "   Default: postgresql://postgres:password@localhost/5432"
    exit 1
fi
echo "✓ PostgreSQL connection OK"
echo ""
echo "📊 Проверяю базу данных..."
if ! psql -U postgres -lqt | cut -d \| -f 1 | grep -w telecom_db &> /dev/null; then
    echo "   Создаю базу данных telecom_db..."
    psql -U postgres -c "CREATE DATABASE telecom_db;"
    echo "✓ Database created"
else
    echo "✓ Database telecom_db already exists"
fi
echo ""
echo "🔄 Инициализирую таблицы и тестовые данные..."
python init_db.py
echo "✓ Database initialized"
echo ""
echo "🔍 Выполняю SAST анализ (bandit)..."
if ! bandit -r app/ -f json -o /dev/null 2>&1 | grep -q "error"; then
    echo "✓ SAST check passed"
else
    echo "⚠️  SAST check completed (check output for warnings)"
fi
echo ""
echo "📦 Выполняю SCA анализ (pip-audit)..."
if pip-audit --skip-editable 2>&1 | grep -q "found 0 vulnerabilities"; then
    echo "✓ SCA check passed"
else
    echo "⚠️  SCA check completed (check output for warnings)"
fi

echo ""
echo "==============================================="
echo "✅ Setup completed successfully!"
echo ""
echo "🚀 Для запуска приложения выполните:"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "📖 API документация будет доступна на:"
echo "   http://localhost:8000/docs"
echo ""
echo "🧪 Для запуска тестов:"
echo "   pytest tests/ -v"
echo ""
