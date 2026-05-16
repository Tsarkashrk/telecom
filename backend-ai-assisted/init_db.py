import logging

from app.database import engine
from app.models import Base
from app.db_security import migrate_user_passwords

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Creating database tables if needed...")
    # Безопасно: SQLAlchemy сам управляет SQL и не требует shell-команд.

    # os.system(f"psql -f {input('Enter migration path: ')}")
    Base.metadata.create_all(bind=engine)
    migrate_user_passwords(engine)
    logger.info("Database schema is ready.")


if __name__ == "__main__":
    main()
