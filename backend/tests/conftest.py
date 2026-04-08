import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from app.database import set_db, get_db_dep
from app.auth import create_token, hash_password

@pytest_asyncio.fixture
async def db():
    client = AsyncMongoMockClient()
    database = client["phenoplant_test"]
    set_db(database)
    yield database
    client.close()

@pytest_asyncio.fixture
async def app(db):
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[get_db_dep] = lambda: db
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
async def auth_token(db):
    user_id = "test-user-id"
    await db.users.insert_one({
        "_id": user_id,
        "email": "test@test.com",
        "name": "Test User",
        "password_hash": hash_password("testpass123"),
        "role": "admin",
        "organizationId": "org1",
    })
    return create_token(user_id, "test@test.com")

@pytest_asyncio.fixture
async def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}
