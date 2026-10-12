import httpx
import pytest
import respx
from jose import jwt

from app.routers import auth as auth_router

pytestmark = pytest.mark.asyncio


class FakeKeycloak:
    """Minimal Keycloak admin + token endpoints backed by a dict of users."""

    def __init__(self):
        self.users = {}  # email -> (id, password)

    def _token(self, email: str) -> dict:
        user_id, _ = self.users[email]
        claims = {"sub": user_id, "email": email, "preferred_username": email,
                  "realm_access": {"roles": ["researcher"]}}
        return {"access_token": jwt.encode(claims, "test", algorithm="HS256"), "refresh_token": f"refresh-{email}"}

    def admin_token(self, request):
        return httpx.Response(200, json={"access_token": "kc-admin"})

    def create_user(self, request):
        import json
        body = json.loads(request.content)
        email = body["email"]
        if email in self.users:
            return httpx.Response(409, json={"errorMessage": "User exists"})
        user_id = f"user-{len(self.users) + 1}"
        self.users[email] = (user_id, body["credentials"][0]["value"])
        return httpx.Response(201, headers={"Location": f"{auth_router.KC_ADMIN_USERS_URL}/{user_id}"})

    def token(self, request):
        from urllib.parse import parse_qs
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        if form.get("grant_type") == "refresh_token":
            email = form["refresh_token"].removeprefix("refresh-")
            return httpx.Response(200, json=self._token(email)) if email in self.users else httpx.Response(400)
        user = self.users.get(form.get("username"))
        if not user or user[1] != form.get("password"):
            return httpx.Response(401, json={"error": "invalid_grant"})
        return httpx.Response(200, json=self._token(form["username"]))


@pytest.fixture
def keycloak():
    kc = FakeKeycloak()
    with respx.mock(assert_all_called=False) as mock:
        mock.post(auth_router.KC_ADMIN_TOKEN_URL).mock(side_effect=kc.admin_token)
        mock.post(auth_router.KC_ADMIN_USERS_URL).mock(side_effect=kc.create_user)
        mock.post(auth_router.KC_TOKEN_URL).mock(side_effect=kc.token)
        mock.get(url__regex=r".*/roles/researcher$").mock(return_value=httpx.Response(200, json={"id": "r1", "name": "researcher"}))
        mock.post(url__regex=r".*/role-mappings/realm$").mock(return_value=httpx.Response(204))
        yield kc


class TestRegister:
    async def test_register_returns_token(self, client, keycloak):
        resp = await client.post("/api/auth/register", json={
            "email": "new@example.com",
            "password": "secret123",
            "name": "New User",
            "organization": "TestOrg",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["email"] == "new@example.com"
        assert data["name"] == "New User"
        assert data["role"] == "researcher"

    async def test_register_duplicate_email_fails(self, client, keycloak):
        payload = {"email": "dup@example.com", "password": "secret123", "name": "Dup"}
        await client.post("/api/auth/register", json=payload)
        resp = await client.post("/api/auth/register", json=payload)
        assert resp.status_code == 409

    async def test_register_short_password_fails(self, client, keycloak):
        resp = await client.post("/api/auth/register", json={
            "email": "short@example.com", "password": "123", "name": "Short"
        })
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client, keycloak):
        await client.post("/api/auth/register", json={
            "email": "login@example.com", "password": "secret123", "name": "Login User"
        })
        resp = await client.post("/api/auth/login", json={
            "email": "login@example.com", "password": "secret123"
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        assert resp.json()["role"] == "researcher"

    async def test_login_wrong_password(self, client, keycloak):
        await client.post("/api/auth/register", json={
            "email": "wrong@example.com", "password": "secret123", "name": "Wrong"
        })
        resp = await client.post("/api/auth/login", json={
            "email": "wrong@example.com", "password": "wrongpass"
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client, keycloak):
        resp = await client.post("/api/auth/login", json={
            "email": "noone@example.com", "password": "whatever"
        })
        assert resp.status_code == 401

    async def test_refresh_token(self, client, keycloak):
        reg = await client.post("/api/auth/register", json={
            "email": "refresh@example.com", "password": "secret123", "name": "R"
        })
        resp = await client.post("/api/auth/refresh", json={"refresh_token": reg.json()["refresh_token"]})
        assert resp.status_code == 200
        assert resp.json()["access_token"]


class TestAccessControl:
    async def test_protected_endpoint_without_token(self, client):
        resp = await client.get("/api/studies")
        assert resp.status_code == 403

    async def test_protected_endpoint_with_invalid_token(self, client):
        resp = await client.get("/api/studies", headers={"Authorization": "Bearer forged"})
        assert resp.status_code == 401

    async def test_protected_endpoint_with_valid_token(self, client, auth_headers):
        resp = await client.get("/api/studies", headers=auth_headers)
        assert resp.status_code == 200
