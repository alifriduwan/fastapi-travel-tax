from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from ..models import get_session
from app.models.province import ProvinceBase, ProvinceCreate, ProvinceRead, DBProvince, ProvinceUpdate
from fastapi.responses import Response

router = APIRouter(prefix="/provinces", tags=["provinces"])

@router.post("/", response_model=ProvinceRead)
async def create_province(
    province: ProvinceCreate,
    session: AsyncSession = Depends(get_session)
):
    db_province = DBProvince.from_orm(province)
    session.add(db_province)
    await session.commit()
    await session.refresh(db_province)
    return _province_with_tax(db_province)

def _province_with_tax(province: DBProvince) -> ProvinceRead:
    tax_reduction = 0.2 if province.is_secondary else 0.1
    return ProvinceRead(
        id=province.id,
        province_name=province.province_name,
        is_secondary=province.is_secondary,
        tax_reduction=tax_reduction
    )

@router.get("/{province_id}", response_model=ProvinceRead)
async def get_province(
    province_id: int,
    session: AsyncSession = Depends(get_session)
):
    province = await session.get(DBProvince, province_id)
    if not province:
        raise HTTPException(status_code=404, detail="Province not found")
    return _province_with_tax(province)

@router.get("/", response_model=list[ProvinceRead])
async def list_provinces(session: AsyncSession = Depends(get_session)):
    result = await session.exec(select(DBProvince))
    provinces = result.all()
    return [_province_with_tax(p) for p in provinces]