from pydantic import BaseModel, ConfigDict
from typing import Optional

class ProvinceBase(BaseModel):
    province_name: str
    is_secondary: bool

class ProvinceCreate(ProvinceBase):
    pass

class ProvinceRead(ProvinceBase):
    id: int
    tax_reduction: float 
    model_config = ConfigDict(from_attributes=True)
