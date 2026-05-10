import pytest
from httpx import AsyncClient

import redis.exceptions as redis_exc
from app.config import settings

pytestmark = pytest.mark.asyncio


async def test_login_success(async_client: AsyncClient, patient_token):
    """Token already obtained in fixture, but we can verify directly."""
    resp = await async_client.post("/login", data={
        "username": "patient@test.com",
        "password": "PatientPass123!"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_invalid_password(async_client: AsyncClient, patient_user):
    resp = await async_client.post("/login", data={
        "username": patient_user.email,
        "password": "WrongPassword!@#"
    })
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Invalid Credentials"


async def test_login_nonexistent_user(async_client: AsyncClient):
    resp = await async_client.post("/login", data={
        "username": "ghost@test.com",
        "password": "whatever"
    })
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Invalid Credentials"


async def test_protected_route_without_token(async_client: AsyncClient):
    resp = await async_client.get("/v1/patients/profile/me")
    assert resp.status_code == 401  # or 403, depends on your middleware


async def test_protected_route_with_invalid_token(async_client: AsyncClient):
    headers = {"Authorization": "Bearer invalidtoken"}
    resp = await async_client.get("/v1/patients/profile/me", headers=headers)
    assert resp.status_code == 401


async def test_logout_sets_blacklist_key(async_client: AsyncClient, patient_token, clean_redis):
    """Logout must place the token's jti into Redis with a TTL."""
    headers = {"Authorization": f"Bearer {patient_token}"}
    resp = await async_client.post("/logout", headers=headers)
    assert resp.status_code == 200

    # Extract jti from token
    import jwt
    payload = jwt.decode(
        patient_token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={"verify_exp": False}   # do not care about expiry
    )
    jti = payload.get("jti")
    assert jti is not None

    # Verify the key was stored in Redis
    exists = await clean_redis.exists(f"blacklist:{jti}")
    assert exists == 1


async def test_blacklisted_token_is_rejected(async_client: AsyncClient, patient_token, clean_redis):
    """A token whose jti is in the blacklist must get 401."""
    import jwt
    payload = jwt.decode(
        patient_token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={"verify_exp": False}
    )
    jti = payload["jti"]

    # Manually blacklist the token
    await clean_redis.set(f"blacklist:{jti}", "true", ex=3600)

    # Try to use it
    headers = {"Authorization": f"Bearer {patient_token}"}
    resp = await async_client.get("/v1/patients/profile/me", headers=headers)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Token has been revoked."


async def test_health_check(async_client: AsyncClient):
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("operational", "degraded")
    assert data["database"] == "healthy"
    assert data["redis"] == "healthy"