import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

import app.auth as auth_module
from app.database import get_brapi_db_dep, get_db_dep
from app.storage import MemoryStorage, get_storage_dep

# Bearer tokens accepted by the fake Keycloak validator and the claims they carry
TOKENS = {
    "admin-token": {"sub": "admin-id", "email": "admin@test.ru", "preferred_username": "admin",
                    "realm_access": {"roles": ["admin"]}},
    "researcher-token": {"sub": "researcher-id", "email": "researcher@test.ru", "preferred_username": "researcher",
                         "realm_access": {"roles": ["researcher"]}},
    "observer-token": {"sub": "observer-id", "email": "observer@test.ru", "preferred_username": "observer",
                       "realm_access": {"roles": ["observer"]}},
}


@pytest.fixture(autouse=True)
def fake_keycloak_tokens(monkeypatch):
    """Validate tokens locally instead of fetching JWKS from Keycloak."""
    async def decode(token: str) -> dict:
        if token not in TOKENS:
            raise HTTPException(status_code=401, detail="Invalid token")
        return TOKENS[token]
    monkeypatch.setattr(auth_module, "decode_keycloak_token", decode)


@pytest_asyncio.fixture
async def mongo():
    client = AsyncMongoMockClient()
    yield client["phenoplant_test"], client["phenoplant_test_brapi"]
    client.close()


@pytest.fixture
def db(mongo):
    return mongo[0]


@pytest.fixture
def brapi_db(mongo):
    return mongo[1]


@pytest.fixture
def storage():
    return MemoryStorage()


@pytest_asyncio.fixture
async def app(db, brapi_db, storage):
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[get_db_dep] = lambda: db
    fastapi_app.dependency_overrides[get_brapi_db_dep] = lambda: brapi_db
    fastapi_app.dependency_overrides[get_storage_dep] = lambda: storage
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer admin-token"}


@pytest.fixture
def researcher_headers():
    return {"Authorization": "Bearer researcher-token"}


@pytest.fixture
def observer_headers():
    return {"Authorization": "Bearer observer-token"}
