from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import datetime
from typing import Annotated

from app.models.user_model import (
    DBUser, RegisteredUser, User, Login, UpdatedUser, ChangedPassword
)
from app.models.province import DBProvince
from app.models import get_session
from app.core.deps import get_current_active_user

router = APIRouter(prefix="/users", tags=["users"])

# Register - ไม่ต้องล็อกอิน
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
    user.register_date = datetime.datetime.now(datetime.timezone.utc)

    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# Login - (ถ้าต้องการ ใช้ /token แทน)
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


# Get current user profile - ต้องล็อกอิน
@router.get("/me", response_model=User)
async def read_users_me(
    current_user: Annotated[DBUser, Depends(get_current_active_user)]
):
    return current_user


# Get user by id - ต้องล็อกอิน
@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    current_user: Annotated[DBUser, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_session)
):
    user = await session.get(DBUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Update user - ต้องล็อกอิน
@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_in: UpdatedUser,
    current_user: Annotated[DBUser, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_session)
):
    user = await session.get(DBUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # (ถ้าต้องการ) ตรวจสอบสิทธิ์ว่า user ตัวเอง หรือ admin ถึงจะแก้ไขได้
    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")

    user_data = user_in.dict(exclude_unset=True)
    for key, value in user_data.items():
        setattr(user, key, value)

    user.updated_date = datetime.datetime.now(datetime.timezone.utc)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


# Change password - ต้องล็อกอิน
@router.post("/{user_id}/change-password")
async def change_password(
    user_id: int,
    pw: ChangedPassword,
    current_user: Annotated[DBUser, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_session)
):
    user = await session.get(DBUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to change password for this user")

    if not user.verify_password(pw.current_password):
        raise HTTPException(status_code=400, detail="Current password incorrect")

    user.set_password(pw.new_password)
    user.updated_date = datetime.datetime.now(datetime.timezone.utc)
    session.add(user)
    await session.commit()

    return {"message": "Password changed successfully"}


# Delete user - ต้องล็อกอิน (และอาจต้องเป็น admin)
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: Annotated[DBUser, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_session)
):
    user = await session.get(DBUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ตรวจสอบสิทธิ์ (เช่น admin หรือ ตัวเอง)
    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this user")

    await session.delete(user)
    await session.commit()
    return


# User tax info - ต้องล็อกอิน
@router.get("/{user_id}/tax-info")
async def get_user_tax_info(
    user_id: int,
    current_user: Annotated[DBUser, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_session)
):
    user = await session.get(DBUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user's tax info")

    if not user.selected_province_id:
        raise HTTPException(status_code=400, detail="User has not selected a province")

    province = await session.get(DBProvince, user.selected_province_id)
    if not province:
        raise HTTPException(status_code=404, detail="Province not found")

    return {
        "user_id": user.id,
        "province_name": province.province_name,
        "is_secondary": province.is_secondary,
        "tax_reduction": 0.2 if province.is_secondary else 0.1
    }


# Select province for user - ต้องล็อกอิน
@router.put("/{user_id}/select-province/{province_id}")
async def select_province(
    user_id: int,
    province_id: int,
    current_user: Annotated[DBUser, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_session)
):
    user = await session.get(DBUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to select province for this user")

    province = await session.get(DBProvince, province_id)
    if not province:
        raise HTTPException(status_code=404, detail="Province not found")

    user.selected_province_id = province_id
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return {"message": f"User {user.id} selected province {province.province_name}"}
