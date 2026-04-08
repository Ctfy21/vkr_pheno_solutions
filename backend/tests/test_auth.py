import pytest

pytestmark = pytest.mark.asyncio

class TestRegister:
    async def test_register_returns_token(self, client):
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

    async def test_register_duplicate_email_fails(self, client):
        payload = {"email": "dup@example.com", "password": "secret123", "name": "Dup"}
        await client.post("/api/auth/register", json=payload)
        resp = await client.post("/api/auth/register", json=payload)
        assert resp.status_code == 409

    async def test_register_short_password_fails(self, client):
        resp = await client.post("/api/auth/register", json={
            "email": "short@example.com", "password": "123", "name": "Short"
        })
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client):
        await client.post("/api/auth/register", json={
            "email": "login@example.com", "password": "secret123", "name": "Login User"
        })
        resp = await client.post("/api/auth/login", json={
            "email": "login@example.com", "password": "secret123"
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_login_wrong_password(self, client):
        await client.post("/api/auth/register", json={
            "email": "wrong@example.com", "password": "secret123", "name": "Wrong"
        })
        resp = await client.post("/api/auth/login", json={
            "email": "wrong@example.com", "password": "wrongpass"
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client):
        resp = await client.post("/api/auth/login", json={
            "email": "noone@example.com", "password": "whatever"
        })
        assert resp.status_code == 401
