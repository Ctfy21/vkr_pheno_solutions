import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.schemas import RegisterRequest, LoginRequest, TokenResponse
from app.config import (
    KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID,
    KEYCLOAK_ADMIN_USER, KEYCLOAK_ADMIN_PASSWORD,
)

router = APIRouter()

KC_TOKEN_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
KC_ADMIN_TOKEN_URL = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
KC_ADMIN_USERS_URL = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users"


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str


async def _get_admin_token() -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(KC_ADMIN_TOKEN_URL, data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": KEYCLOAK_ADMIN_USER,
            "password": KEYCLOAK_ADMIN_PASSWORD,
        }, timeout=10)
        resp.raise_for_status()
        return resp.json()["access_token"]


async def _get_user_roles(admin_token: str, user_id: str) -> list:
    url = f"{KC_ADMIN_USERS_URL}/{user_id}/role-mappings/realm"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {admin_token}"}, timeout=10)
        if resp.status_code == 200:
            return [r["name"] for r in resp.json()]
    return []


def _pick_role(roles: list) -> str:
    if "admin" in roles:
        return "admin"
    if "researcher" in roles:
        return "researcher"
    return "observer"


async def _assign_role(admin_token: str, user_id: str, role_name: str):
    url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/roles/{role_name}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {admin_token}"}, timeout=10)
        if resp.status_code != 200:
            return
        role = resp.json()
        assign_url = f"{KC_ADMIN_USERS_URL}/{user_id}/role-mappings/realm"
        await client.post(
            assign_url,
            json=[role],
            headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            timeout=10,
        )


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    admin_token = await _get_admin_token()

    user_payload = {
        "username": req.email,
        "email": req.email,
        "firstName": req.name,
        "lastName": "",
        "enabled": True,
        "emailVerified": True,
        "credentials": [{"type": "password", "value": req.password, "temporary": False}],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            KC_ADMIN_USERS_URL,
            json=user_payload,
            headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code == 409:
            raise HTTPException(status_code=409, detail="Email already registered")
        if resp.status_code not in (201, 204):
            raise HTTPException(status_code=500, detail=f"Keycloak error: {resp.text}")

        location = resp.headers.get("location", "")
        user_id = location.split("/")[-1] if location else ""

    if user_id:
        await _assign_role(admin_token, user_id, "researcher")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(KC_TOKEN_URL, data={
            "grant_type": "password",
            "client_id": KEYCLOAK_CLIENT_ID,
            "username": req.email,
            "password": req.password,
        }, timeout=10)
        if token_resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Registration succeeded but login failed")
        token_data = token_resp.json()

    return TokenResponse(
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token", ""),
        user_id=user_id,
        name=req.name,
        email=req.email,
        role="researcher",
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    async with httpx.AsyncClient() as client:
        resp = await client.post(KC_TOKEN_URL, data={
            "grant_type": "password",
            "client_id": KEYCLOAK_CLIENT_ID,
            "username": req.email,
            "password": req.password,
        }, timeout=10)

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token_data = resp.json()
    access_token = token_data["access_token"]

    from jose import jwt as jose_jwt
    payload = jose_jwt.get_unverified_claims(access_token)
    roles = payload.get("realm_access", {}).get("roles", [])

    return TokenResponse(
        access_token=access_token,
        refresh_token=token_data.get("refresh_token", ""),
        user_id=payload.get("sub", ""),
        name=payload.get("preferred_username", payload.get("name", "")),
        email=payload.get("email", req.email),
        role=_pick_role(roles),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(req: RefreshRequest):
    async with httpx.AsyncClient() as client:
        resp = await client.post(KC_TOKEN_URL, data={
            "grant_type": "refresh_token",
            "client_id": KEYCLOAK_CLIENT_ID,
            "refresh_token": req.refresh_token,
        }, timeout=10)

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    token_data = resp.json()
    return RefreshResponse(
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token", req.refresh_token),
    )
