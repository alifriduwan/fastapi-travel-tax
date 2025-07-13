import pytest
import pytest_asyncio
import httpx
from httpx import AsyncClient
from app.main import app
from sqlmodel import SQLModel

from app.models import get_session
from app.models.user_model import DBUser
from app.models.province import DBProvince
from app.core.deps import get_current_active_user

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import datetime


@pytest_asyncio.fixture
async def engine():
    """Create test database engine."""
    load_dotenv(dotenv_path=".env.test")
    sql_url = os.getenv("SQL_CONNECTION_STRING")
    engine = create_async_engine(
        sql_url,
        connect_args=(
            {"check_same_thread": False} if sql_url.startswith("sqlite") else {}
        ),
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine):
    """Create test database session."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def client(session):
    """Create test client with dependency override."""

    async def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override

    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://localhost:8000"
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(session):
    """Create a test user in database."""
    user = DBUser(
        email="test@example.com",
        phone_number="1234567890",
        username="testuser",
        first_name="Test",
        last_name="User",
        roles=[],
        register_date=datetime.datetime.now(datetime.timezone.utc)
    )
    user.set_password("testpassword")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_province(session):
    """Create a test province in database."""
    province = DBProvince(
        province_name="Test Province",
        is_secondary=True
    )
    session.add(province)
    await session.commit()
    await session.refresh(province)
    return province


@pytest_asyncio.fixture
async def authenticated_client(client, session, test_user):
    """Create authenticated client."""
    
    async def get_current_user_override():
        return test_user

    app.dependency_overrides[get_current_active_user] = get_current_user_override
    
    yield client
    
    # Clean up override
    if get_current_active_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_active_user]


@pytest.fixture
def register_data():
    return {
        "email": "newuser@example.com",
        "phone_number": "0987654321",
        "username": "newuser",
        "first_name": "New",
        "last_name": "User",
        "password": "newpassword123"
    }


@pytest.fixture
def login_data():
    return {
        "identifier": "test@example.com",
        "password": "testpassword"
    }


# Test user registration
@pytest.mark.asyncio
async def test_register_user(client, register_data):
    response = await client.post("/users/register", json=register_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == register_data["email"]
    assert data["username"] == register_data["username"]
    assert data["first_name"] == register_data["first_name"]
    assert data["last_name"] == register_data["last_name"]
    assert "id" in data
    assert "password" not in data  # Password should not be returned


@pytest.mark.asyncio
async def test_register_duplicate_email(client, register_data, test_user):
    # Try to register with existing email
    register_data["email"] = test_user.email
    response = await client.post("/users/register", json=register_data)
    
    assert response.status_code == 400
    assert "Email or phone already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_phone(client, register_data, test_user):
    # Try to register with existing phone number
    register_data["phone_number"] = test_user.phone_number
    response = await client.post("/users/register", json=register_data)
    
    assert response.status_code == 400
    assert "Email or phone already registered" in response.json()["detail"]


# Test login
@pytest.mark.asyncio
async def test_login_success(client, login_data, test_user):
    response = await client.post("/users/login", json=login_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Login success"
    assert data["user_id"] == test_user.id


@pytest.mark.asyncio
async def test_login_with_phone(client, test_user):
    login_data = {
        "identifier": test_user.phone_number,
        "password": "testpassword"
    }
    response = await client.post("/users/login", json=login_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Login success"
    assert data["user_id"] == test_user.id


@pytest.mark.asyncio
async def test_login_invalid_credentials(client, login_data):
    login_data["password"] = "wrongpassword"
    response = await client.post("/users/login", json=login_data)
    
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_user_not_found(client):
    login_data = {
        "identifier": "nonexistent@example.com",
        "password": "anypassword"
    }
    response = await client.post("/users/login", json=login_data)
    
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


# Test get current user
@pytest.mark.asyncio
async def test_get_current_user(authenticated_client, test_user):
    response = await authenticated_client.get("/users/me")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert data["username"] == test_user.username


# Test get user by ID
@pytest.mark.asyncio
async def test_get_user_by_id(authenticated_client, test_user):
    response = await authenticated_client.get(f"/users/{test_user.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email


@pytest.mark.asyncio
async def test_get_user_not_found(authenticated_client):
    response = await authenticated_client.get("/users/99999")
    
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


# Test update user
@pytest.mark.asyncio
async def test_update_user(authenticated_client, test_user):
    update_data = {
        "first_name": "Updated",
        "last_name": "Name"
    }
    response = await authenticated_client.put(f"/users/{test_user.id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "Name"


@pytest.mark.asyncio
async def test_update_user_not_found(authenticated_client):
    update_data = {"first_name": "Updated"}
    response = await authenticated_client.put("/users/99999", json=update_data)
    
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_user_unauthorized(authenticated_client, session):
    # Create another user
    other_user = DBUser(
        email="other@example.com",
        phone_number="0000000000",
        username="otheruser",
        first_name="Other",
        last_name="User",
        roles=[]
    )
    session.add(other_user)
    await session.commit()
    await session.refresh(other_user)
    
    update_data = {"first_name": "Updated"}
    response = await authenticated_client.put(f"/users/{other_user.id}", json=update_data)
    
    assert response.status_code == 403
    assert "Not authorized to update this user" in response.json()["detail"]


# Test change password
@pytest.mark.asyncio
async def test_change_password(authenticated_client, test_user):
    password_data = {
        "current_password": "testpassword",
        "new_password": "newpassword123"
    }
    response = await authenticated_client.post(f"/users/{test_user.id}/change-password", json=password_data)
    
    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully"


@pytest.mark.asyncio
async def test_change_password_incorrect_current(authenticated_client, test_user):
    password_data = {
        "current_password": "wrongpassword",
        "new_password": "newpassword123"
    }
    response = await authenticated_client.post(f"/users/{test_user.id}/change-password", json=password_data)
    
    assert response.status_code == 400
    assert "Current password incorrect" in response.json()["detail"]


@pytest.mark.asyncio
async def test_change_password_unauthorized(authenticated_client, session):
    # Create another user
    other_user = DBUser(
        email="other@example.com",
        phone_number="0000000000",
        username="otheruser",
        first_name="Other",
        last_name="User",
        roles=[]
    )
    session.add(other_user)
    await session.commit()
    await session.refresh(other_user)
    
    password_data = {
        "current_password": "testpassword",
        "new_password": "newpassword123"
    }
    response = await authenticated_client.post(f"/users/{other_user.id}/change-password", json=password_data)
    
    assert response.status_code == 403
    assert "Not authorized to change password for this user" in response.json()["detail"]


# Test delete user
@pytest.mark.asyncio
async def test_delete_user(authenticated_client, test_user):
    response = await authenticated_client.delete(f"/users/{test_user.id}")
    
    assert response.status_code == 204
    
    # Verify user is deleted
    get_response = await authenticated_client.get(f"/users/{test_user.id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_not_found(authenticated_client):
    response = await authenticated_client.delete("/users/99999")
    
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


# Test tax info
@pytest.mark.asyncio
async def test_get_user_tax_info(authenticated_client, test_user, test_province, session):
    # Set user's selected province
    test_user.selected_province_id = test_province.id
    session.add(test_user)
    await session.commit()
    
    response = await authenticated_client.get(f"/users/{test_user.id}/tax-info")
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == test_user.id
    assert data["province_name"] == test_province.province_name
    assert data["is_secondary"] == test_province.is_secondary
    assert data["tax_reduction"] == 0.2  # Because is_secondary is True


@pytest.mark.asyncio
async def test_get_user_tax_info_no_province(authenticated_client, test_user):
    response = await authenticated_client.get(f"/users/{test_user.id}/tax-info")
    
    assert response.status_code == 400
    assert "User has not selected a province" in response.json()["detail"]


# Test select province
@pytest.mark.asyncio
async def test_select_province(authenticated_client, test_user, test_province):
    response = await authenticated_client.put(f"/users/{test_user.id}/select-province/{test_province.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert f"User {test_user.id} selected province {test_province.province_name}" in data["message"]


@pytest.mark.asyncio
async def test_select_province_not_found(authenticated_client, test_user):
    response = await authenticated_client.put(f"/users/{test_user.id}/select-province/99999")
    
    assert response.status_code == 404
    assert "Province not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_select_province_user_not_found(authenticated_client, test_province):
    response = await authenticated_client.put(f"/users/99999/select-province/{test_province.id}")
    
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


# Test unauthenticated access
@pytest.mark.asyncio
async def test_unauthenticated_access_to_protected_route(client):
    response = await client.get("/users/me")
    
    # This should return 401 or 403 depending on your auth implementation
    assert response.status_code in [401, 403]