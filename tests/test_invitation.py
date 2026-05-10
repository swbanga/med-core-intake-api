import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_invite_user_success(async_client: AsyncClient, admin_token, seeded_roles):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.post(
        "/v1/identity/invite",
        json={"email": "newdoc@test.com", "role_name": "Doctor"},
        headers=headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "activation_url" in data
    # extract token from URL
    url = data["activation_url"]
    token = url.split("token=")[-1]
    assert len(token) > 10  # sanity check


async def test_invite_duplicate_email(async_client: AsyncClient, admin_token, db_session):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # first invite – successful
    resp1 = await async_client.post(
        "/v1/identity/invite",
        json={"email": "dup@test.com", "role_name": "Patient"},
        headers=headers
    )
    assert resp1.status_code == 201

    # force any pending writes (just for paranoia)
    await db_session.flush()

    # second invite – must be rejected
    resp2 = await async_client.post(
        "/v1/identity/invite",
        json={"email": "dup@test.com", "role_name": "Patient"},
        headers=headers
    )
    assert resp2.status_code == 409


async def test_invite_nonexistent_role(async_client: AsyncClient, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.post(
        "/v1/identity/invite",
        json={"email": "badrole@test.com", "role_name": "GhostRole"},
        headers=headers
    )
    assert resp.status_code == 400  # role not found


async def test_activate_account(async_client: AsyncClient, admin_token, db_session):
    """Full invite -> activate -> login cycle."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    invite_resp = await async_client.post(
        "/v1/identity/invite",
        json={"email": "activate@test.com", "role_name": "Patient"},
        headers=headers
    )
    token = invite_resp.json()["activation_url"].split("token=")[-1]

    # Activate with password
    activate_resp = await async_client.post(
        "/v1/identity/activate",
        json={"token": token, "password": "ActivatePass1234"}
    )
    assert activate_resp.status_code == 200

    # Login with the new password
    login_resp = await async_client.post("/login", data={
        "username": "activate@test.com",
        "password": "ActivatePass1234"
    })
    assert login_resp.status_code == 200


async def test_activate_with_invalid_token(async_client: AsyncClient):
    resp = await async_client.post(
        "/v1/identity/activate",
        json={"token": "bad.token.here", "password": "Whatever12345"}
    )
    assert resp.status_code == 400


async def test_invite_without_admin(async_client: AsyncClient, patient_token):
    headers = {"Authorization": f"Bearer {patient_token}"}
    resp = await async_client.post(
        "/v1/identity/invite",
        json={"email": "nope@test.com", "role_name": "Patient"},
        headers=headers
    )
    assert resp.status_code == 403