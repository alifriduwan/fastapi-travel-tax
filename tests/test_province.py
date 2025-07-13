import pytest
import pytest_asyncio
import httpx
from httpx import AsyncClient
from app.main import app
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

from app.models import get_session
from app.models.province import DBProvince
from app.models.user_model import DBUser
from app.core.deps import get_current_active_user, get_current_user, RoleChecker


@pytest_asyncio.fixture(scope="function")
async def engine():
    """สร้าง engine และฐานข้อมูลใหม่สำหรับแต่ละฟังก์ชันเทส."""
    load_dotenv(dotenv_path=".env.test")
    sql_url = os.getenv("SQL_CONNECTION_STRING")
    engine = create_async_engine(
        sql_url,
        connect_args=({"check_same_thread": False} if sql_url.startswith("sqlite") else {})
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def mock_admin_user(session):
    admin_user = DBUser(
        id=1,
        email="admin@test.com",
        phone_number="1234567890",
        username="admin",
        first_name="Admin",
        last_name="User",
        roles=["admin"] 
    )
    admin_user.set_password("password123")
    session.add(admin_user)
    await session.commit()
    await session.refresh(admin_user)
    return admin_user


@pytest_asyncio.fixture
async def mock_normal_user(session):
    """สร้าง mock normal user สำหรับการทดสอบ."""
    normal_user = DBUser(
        id=2,
        email="user@test.com",
        phone_number="0987654321",
        username="user",
        first_name="Normal",
        last_name="User",
        roles=["user"]
    )
    normal_user.set_password("password123")
    session.add(normal_user)
    await session.commit()
    await session.refresh(normal_user)
    return normal_user


@pytest_asyncio.fixture
async def admin_client(session, mock_admin_user):
    async def get_session_override():
        yield session

    async def get_current_user_override():
        return mock_admin_user

    async def get_current_active_user_override():
        return mock_admin_user

    class MockRoleChecker:
        def __init__(self, *allowed_roles: str):
            self.allowed_roles = allowed_roles
        def __call__(self, user: DBUser = None):
            return True

    original_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_current_user] = get_current_user_override
    app.dependency_overrides[get_current_active_user] = get_current_active_user_override
    app.dependency_overrides[RoleChecker] = MockRoleChecker

    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides = original_overrides


@pytest_asyncio.fixture
async def normal_client(session, mock_normal_user):
    """สร้าง Test Client ที่ไม่มีสิทธิ์ Admin."""

    async def get_session_override():
        yield session

    async def get_current_user_override():
        return mock_normal_user

    async def get_current_active_user_override():
        return mock_normal_user

    original_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_current_user] = get_current_user_override
    app.dependency_overrides[get_current_active_user] = get_current_active_user_override

    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides = original_overrides


@pytest_asyncio.fixture
async def test_province(session):
    province = DBProvince(province_name="Test Province", is_secondary=True)
    session.add(province)
    await session.commit()
    await session.refresh(province)
    return province


# ---------- TEST CASES ---------- #

@pytest.mark.asyncio
async def test_create_province(admin_client):
    """Test creating a province with admin client."""
    data = {"province_name": "New Province", "is_secondary": False}
    response = await admin_client.post("/provinces/", json=data)
    
    if response.status_code != 200:
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.content}")
    
    assert response.status_code == 200
    result = response.json()
    assert result["province_name"] == data["province_name"]
    assert result["is_secondary"] == data["is_secondary"]
    assert "id" in result


@pytest.mark.asyncio
async def test_create_province_unauthenticated(normal_client):
    """Test creating a province with normal user (should fail)."""
    data = {"province_name": "New Province", "is_secondary": False}
    response = await normal_client.post("/provinces/", json=data)
    assert response.status_code == 401 or response.status_code == 403


@pytest.mark.asyncio
async def test_get_province(admin_client, test_province):
    """Test getting a province."""
    response = await admin_client.get(f"/provinces/{test_province.id}")
    assert response.status_code == 200
    result = response.json()
    assert result["province_name"] == test_province.province_name


@pytest.mark.asyncio
async def test_get_province_not_found(admin_client):
    """Test getting a non-existent province."""
    response = await admin_client.get("/provinces/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_provinces(admin_client, test_province):
    """Test listing provinces."""
    response = await admin_client.get("/provinces/")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert any(p["province_name"] == test_province.province_name for p in result)


@pytest.mark.asyncio
async def test_update_province(admin_client, test_province):
    """Test updating a province with admin client."""
    update_data = {"province_name": "Updated Province", "is_secondary": False}
    response = await admin_client.put(f"/provinces/{test_province.id}", json=update_data)
    assert response.status_code == 200
    result = response.json()
    assert result["province_name"] == update_data["province_name"]
    assert result["is_secondary"] == update_data["is_secondary"]


@pytest.mark.asyncio
async def test_update_province_not_found(admin_client):
    """Test updating a non-existent province."""
    update_data = {"province_name": "Updated Province", "is_secondary": False}
    response = await admin_client.put("/provinces/99999", json=update_data)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_province_unauthenticated(normal_client, test_province):
    """Test updating a province with normal user (should fail)."""
    update_data = {"province_name": "Updated Province", "is_secondary": False}
    response = await normal_client.put(f"/provinces/{test_province.id}", json=update_data)
    assert response.status_code == 401 or response.status_code == 403


@pytest.mark.asyncio
async def test_delete_province(admin_client, test_province):
    """Test deleting a province with admin client."""
    response = await admin_client.delete(f"/provinces/{test_province.id}")
    assert response.status_code == 204 

    get_response = await admin_client.get(f"/provinces/{test_province.id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_province_not_found(admin_client):
    """Test deleting a non-existent province."""
    response = await admin_client.delete("/provinces/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_province_unauthenticated(normal_client, test_province):
    """Test deleting a province with normal user (should fail)."""
    response = await normal_client.delete(f"/provinces/{test_province.id}")
    assert response.status_code == 401 or response.status_code == 403