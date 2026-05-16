# Backend AI-Assisted

Отдельный backend-проект для задания 2. Эта версия функционально эквивалентна backend из задания 1, но оформлена как самостоятельный серверный контур для AI-assisted продукта.

## Запуск

```bash
cd backend-ai-assisted
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

## Технологии

- FastAPI
- SQLAlchemy
- JWT
- Pydantic
- Pytest

## Назначение

- обслуживает `frontend-ai-assisted/`;
- реализует тот же secure business flow;
- поддерживает роли `customer`, `operator`, `admin`;
- включает аутентификацию, биллинг, подписки, аудит и OWASP-oriented controls.
