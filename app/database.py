from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
from typing import Generator

# Создание engine для PostgreSQL
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Проверяет соединение перед использованием
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Генератор сессии БД для dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
