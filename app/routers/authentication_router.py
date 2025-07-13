from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from typing import Annotated
import datetime

from app import models
from app.core import config, security

router = APIRouter(tags=["authentication"])
settings = config.get_settings()

@router.post("/token", response_model=models.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[models.AsyncSession, Depends(models.get_session)]
):
    result = await session.exec(select(models.DBUser).where(models.DBUser.username == form_data.username))
    user = result.one_or_none()

    if not user:
        result = await session.exec(select(models.DBUser).where(models.DBUser.email == form_data.username))
        user = result.one_or_none()

    if not user or not user.verify_password(form_data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    user.last_login_date = datetime.datetime.now(datetime.timezone.utc)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    access_token_expires = datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
    refresh_token = security.create_refresh_token(data={"sub": str(user.id)})

    return models.Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        scope="",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        expires_at=datetime.datetime.now(datetime.timezone.utc) + access_token_expires,
        issued_at=user.last_login_date,
        user_id=user.id,
    )
