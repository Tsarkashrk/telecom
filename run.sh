#!/bin/bash

echo "🚀 Запуск Телекоммуникационной платформы MVP"
echo "============================================"
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment не активирована"
    echo "Выполните: source venv/bin/activate"
    exit 1
fi

echo ""
echo "📖 Документация: http://localhost:8000/docs"
echo "📊 Health check: http://localhost:8000/health"
echo ""
echo "🧪 Для остановки: Ctrl+C"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
