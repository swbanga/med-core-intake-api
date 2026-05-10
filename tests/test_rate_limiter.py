import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_login_rate_limit(async_client: AsyncClient):
    # Fire 5 requests (limit is 5 per 60s)
    for _ in range(5):
        resp = await async_client.post("/login", data={
            "username": "nobody@test.com",
            "password": "wrong"
        })
        assert resp.status_code in (403, 429)  # may be 403 on first few

    # 6th request must be 429
    resp = await async_client.post("/login", data={
        "username": "nobody@test.com",
        "password": "wrong"
    })
    assert resp.status_code == 429


async def test_logout_rate_limit(async_client: AsyncClient, patient_token):
    headers = {"Authorization": f"Bearer {patient_token}"}
    for _ in range(10):  # limit is 10
        resp = await async_client.post("/logout", headers=headers)
        # might get 200, after limit 429
    resp = await async_client.post("/logout", headers=headers)
    assert resp.status_code == 429