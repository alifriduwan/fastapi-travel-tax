from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from ..models import get_session
from app.models.province import ProvinceCreate, ProvinceRead, DBProvince, ProvinceUpdate
from app.core.deps import RoleChecker

router = APIRouter(prefix="/provinces", tags=["provinces"])

# Role checker instance for admin role
admin_required = RoleChecker("admin")


def _province_with_tax(province: DBProvince) -> ProvinceRead:
    tax_reduction = 0.2 if province.is_secondary else 0.1
    return ProvinceRead(
        id=province.id,
        province_name=province.province_name,
        is_secondary=province.is_secondary,
        tax_reduction=tax_reduction
    )


@router.post("/", response_model=ProvinceRead, dependencies=[Depends(admin_required)])
async def create_province(
    province: ProvinceCreate,
    session: AsyncSession = Depends(get_session)
):
    db_province = DBProvince.from_orm(province)
    session.add(db_province)
    await session.commit()
    await session.refresh(db_province)
    return _province_with_tax(db_province)


@router.get("/{province_id}", response_model=ProvinceRead)
async def get_province(
    province_id: int,
    session: AsyncSession = Depends(get_session)
):
    province = await session.get(DBProvince, province_id)
    if not province:
        raise HTTPException(status_code=404, detail="Province not found")
    return _province_with_tax(province)


@router.get("/", response_model=List[ProvinceRead])
async def list_provinces(session: AsyncSession = Depends(get_session)):
    result = await session.exec(select(DBProvince))
    provinces = result.all()
    return [_province_with_tax(p) for p in provinces]


@router.put("/{province_id}", response_model=ProvinceRead, dependencies=[Depends(admin_required)])
async def update_province(
    province_id: int,
    province_in: ProvinceUpdate,
    session: AsyncSession = Depends(get_session)
):
    province = await session.get(DBProvince, province_id)
    if not province:
        raise HTTPException(status_code=404, detail="Province not found")

    update_data = province_in.model_dump(exclude_unset=True)  # Pydantic v2
    for key, value in update_data.items():
        setattr(province, key, value)

    session.add(province)
    await session.commit()
    await session.refresh(province)
    return _province_with_tax(province)


@router.delete("/{province_id}", status_code=204, dependencies=[Depends(admin_required)])
async def delete_province(
    province_id: int,
    session: AsyncSession = Depends(get_session)
):
    province = await session.get(DBProvince, province_id)
    if not province:
        raise HTTPException(status_code=404, detail="Province not found")

    await session.delete(province)
    await session.commit()
    return Response(status_code=204)
