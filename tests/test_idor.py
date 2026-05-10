import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def create_patient_profile(client: AsyncClient, token: str, first_name="John", last_name="Doe"):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "date_of_birth": "1990-01-01",
        "medical_history": "Allergies"
    }
    resp = await client.post("/v1/patients/profile", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()


async def test_patient_creates_and_reads_own_profile(async_client: AsyncClient, patient_token):
    profile = await create_patient_profile(async_client, patient_token, "Alice", "Patient")
    headers = {"Authorization": f"Bearer {patient_token}"}
    resp = await async_client.get("/v1/patients/profile/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Alice"


async def test_patient_cannot_access_another_patient(
    async_client: AsyncClient, patient_token, second_patient_token
):
    # First patient creates a profile
    headers1 = {"Authorization": f"Bearer {patient_token}"}
    create_resp = await async_client.post("/v1/patients/profile", json={
        "first_name": "Eve",
        "last_name": "Target",
        "date_of_birth": "1992-02-02",
        "medical_history": "Secret"
    }, headers=headers1)
    profile_id = create_resp.json()["id"]

    # Second patient tries to read it
    headers2 = {"Authorization": f"Bearer {second_patient_token}"}
    resp = await async_client.get(f"/v1/patients/profile/{profile_id}", headers=headers2)
    assert resp.status_code == 403

async def test_doctor_can_read_any_patient(async_client: AsyncClient, patient_token, doctor_token):
    profile = await create_patient_profile(async_client, patient_token, "Charlie", "Brown")
    headers = {"Authorization": f"Bearer {doctor_token}"}
    resp = await async_client.get(f"/v1/patients/profile/{profile['id']}", headers=headers)
    assert resp.status_code == 200


async def test_auditor_can_read_but_not_modify(async_client: AsyncClient, patient_token, auditor_token):
    profile = await create_patient_profile(async_client, patient_token, "Diana", "AuditTest")
    headers = {"Authorization": f"Bearer {auditor_token}"}
    # Read
    resp = await async_client.get(f"/v1/patients/profile/{profile['id']}", headers=headers)
    assert resp.status_code == 200
    # Try to modify
    update_resp = await async_client.put(
        f"/v1/patients/{profile['id']}",
        json={"medical_history": "Tampered"},
        headers=headers
    )
    assert update_resp.status_code == 403


async def test_patient_cannot_list_all_profiles(async_client: AsyncClient, patient_token):
    headers = {"Authorization": f"Bearer {patient_token}"}
    resp = await async_client.get("/v1/patients/", headers=headers)
    assert resp.status_code == 403