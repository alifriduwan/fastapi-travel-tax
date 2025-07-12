import datetime
from typing import Annotated, Optional, List

import bcrypt
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    StringConstraints, 
    Field
)
from sqlmodel import SQLModel, Field as ORMField
from sqlalchemy import Column, String, JSON


class BaseUser(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    email: Optional[EmailStr] = Field(
        default=None,
        json_schema_extra=dict(example="admin@email.local")
    )

    phone_number: Annotated[
        str,
        StringConstraints(min_length=8, max_length=15)
    ] = Field(
        json_schema_extra=dict(example="0812345678")
    )

    username: str = Field(json_schema_extra=dict(example="admin"))
    first_name: str = Field(json_schema_extra=dict(example="Firstname"))
    last_name: str = Field(json_schema_extra=dict(example="Lastname"))


class User(BaseUser):
    id: int

    last_login_date: Optional[datetime.datetime] = Field(
        default=None,
        json_schema_extra=dict(example="2023-01-01T00:00:00.000000")
    )
    register_date: Optional[datetime.datetime] = Field(
        default=None,
        json_schema_extra=dict(example="2023-01-01T00:00:00.000000")
    )


class ReferenceUser(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    username: str
    first_name: str
    last_name: str


class UserList(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    users: List[User]


class Login(BaseModel):
    identifier: str = Field(
        json_schema_extra=dict(example="0812345678 or admin@email.local")
    )
    password: str = Field(json_schema_extra=dict(example="YourSecurePassword"))


class RegisteredUser(BaseUser):
    password: str = Field(json_schema_extra=dict(example="YourSecurePassword"))


class UpdatedUser(BaseUser):
    roles: List[str] = Field(
        json_schema_extra=dict(example=["user", "admin"])
    )

class ResetedPassword(BaseModel):
    email: EmailStr = Field(json_schema_extra=dict(example="user@email.local"))
    citizen_id: str = Field(json_schema_extra=dict(example="1103700123456"))


class ChangedPassword(BaseModel):
    current_password: str = Field(json_schema_extra=dict(example="OldPassword123"))
    new_password: str = Field(json_schema_extra=dict(example="NewPassword456"))


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    expires_at: datetime.datetime
    scope: str
    issued_at: datetime.datetime
    user_id: int


from sqlmodel import Column, String, ARRAY
import datetime
from typing import  Optional, List

import bcrypt
from pydantic import (
    EmailStr,
)

class DBUser(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = ORMField(default=None, primary_key=True)

    email: Optional[EmailStr] = ORMField(default=None, unique=True, index=True)
    phone_number: str = ORMField(unique=True, index=True)
    selected_province_id: Optional[int] = ORMField(foreign_key="provinces.id")

    username: str = ORMField(index=True)
    first_name: str
    last_name: str

    hashed_password: str

    roles: List[str] = ORMField(
        sa_column=Column(JSON), default_factory=list
    )

    register_date: datetime.datetime = ORMField(
        default_factory=datetime.datetime.utcnow
    )
    updated_date: datetime.datetime = ORMField(
        default_factory=datetime.datetime.utcnow
    )
    last_login_date: Optional[datetime.datetime] = ORMField(default=None)

    def verify_password(self, plain_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            self.hashed_password.encode("utf-8")
        )

    def set_password(self, plain_password: str) -> None:
        self.hashed_password = bcrypt.hashpw(
            plain_password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

    def has_roles(self, roles: List[str]) -> bool:
        return any(role in self.roles for role in roles)