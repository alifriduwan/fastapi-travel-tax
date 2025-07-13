from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from typing import Annotated
from app import models
from . import config, security

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
settings = config.get_settings()

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[models.AsyncSession, Depends(models.get_session)],
) -> models.DBUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except Exception:
        raise credentials_exception

    user = await session.get(models.DBUser, user_id)
    if not user:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[models.DBUser, Depends(get_current_user)]
) -> models.DBUser:
    return current_user

class RoleChecker:
    def __init__(self, *allowed_roles: str):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        user: Annotated[models.DBUser, Depends(get_current_active_user)]
    ):
        if any(role in self.allowed_roles for role in user.roles):
            return
        raise HTTPException(status_code=403, detail="Role not permitted")
