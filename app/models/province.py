from pydantic import BaseModel, ConfigDict
from typing import Optional
from sqlmodel import SQLModel, Field as ORMField

class ProvinceBase(BaseModel):
    province_name: str
    is_secondary: bool

class ProvinceCreate(ProvinceBase):
    pass

class ProvinceRead(ProvinceBase):
    id: int
    tax_reduction: float 
    model_config = ConfigDict(from_attributes=True)

class ProvinceUpdate(BaseModel):
    province_name: Optional[str] = None
    is_secondary: Optional[bool] = None


class DBProvince(SQLModel, table=True):
    __tablename__ = "provinces"

    id: int | None = ORMField(default=None, primary_key=True)
    province_name: str = ORMField(unique=True, index=True)
    is_secondary: bool = ORMField(default=False)