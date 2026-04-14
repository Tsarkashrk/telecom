from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import verify_token
from app.models import User
from typing import Optional

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Зависимость для получения текущего пользователя из токена.
    Проверяет валидность токена и наличие пользователя в БД.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверные учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise credentials_exception

    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise credentials_exception

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен"
        )

    return user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Зависимость для проверки роли администратора.
    Проверяется на серверной стороне.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуется роль администратора"
        )
    return current_user


async def get_current_operator(current_user: User = Depends(get_current_user)) -> User:
    """
    Зависимость для проверки роли оператора или администратора.
    """
    if current_user.role not in ["operator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуется роль оператора или администратора"
        )
    return current_user


async def verify_object_access(
    resource_owner_id: int,
    current_user: User
) -> bool:
    """
    Проверка доступа к конкретному объекту.
    Клиент может видеть только свои данные, если не администратор.
    """
    if current_user.role == "admin":
        return True
    
    if current_user.id == resource_owner_id:
        return True
    
    return False
