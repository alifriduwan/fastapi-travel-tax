from fastapi import APIRouter, Depends, HTTPException , status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import datetime

from app.models.user_model import (
    DBUser, RegisteredUser, User, Login
)

from ..models import get_session
import datetime

router = APIRouter(prefix="/users", tags=["users"])

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/register", response_model=User)
async def register(user_in: RegisteredUser, session: AsyncSession = Depends(get_session)):
    q = select(DBUser).where(
        (DBUser.email == user_in.email) | (DBUser.phone_number == user_in.phone_number)
    )
    result = await session.exec(q)
    if result.first():
        raise HTTPException(status_code=400, detail="Email or phone already registered")

    user = DBUser(
        email=user_in.email,
        phone_number=user_in.phone_number,
        username=user_in.username,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        roles=[]
    )
    user.set_password(user_in.password)
    user.register_date = datetime.datetime.utcnow()

    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login")
async def login(login_in: Login, session: AsyncSession = Depends(get_session)):
    q = select(DBUser).where(
        (DBUser.email == login_in.identifier) | (DBUser.phone_number == login_in.identifier)
    )
    result = await session.exec(q)
    user = result.first()
    if not user or not user.verify_password(login_in.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"message": "Login success", "user_id": user.id}