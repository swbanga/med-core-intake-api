import pytest
from httpx import AsyncClient
import uuid
from app.models import PatientProfile

pytestmark = pytest.mark.asyncio


async def test_concurrent_profile_update(
    async_client: AsyncClient,
    patient_token,
    doctor_token,
    db_session,
):
    # 1. Patient creates profile
    headers_patient = {"Authorization": f"Bearer {patient_token}"}
    create_resp = await async_client.post(
        "/v1/patients/profile",
        json={
            "first_name": "Con",
            "last_name": "Currency",
            "date_of_birth": "1995-05-05",
            "medical_history": "Stable",
        },
        headers=headers_patient,
    )
    assert create_resp.status_code == 201
    profile_id = create_resp.json()["id"]
    initial_version = create_resp.json()["version"]

    # 2. Doctor fetches the profile to get the current version
    headers_doctor = {"Authorization": f"Bearer {doctor_token}"}
    get_resp = await async_client.get(
        f"/v1/patients/profile/{profile_id}",
        headers=headers_doctor,
    )
    assert get_resp.status_code == 200
    doctor_seen_version = get_resp.json()["version"]

    # 3. Tamper the version in the DB (simulate someone else updating)
    stmt = (
        PatientProfile.__table__.update() # type: ignore
        .where(PatientProfile.id == uuid.UUID(profile_id))
        .values(version=999)
    )
    await db_session.execute(stmt)
    await db_session.commit()

    # 4. Doctor tries to update using the stale version – must get 409
    update2 = await async_client.put(
        f"/v1/patients/{profile_id}",
        json={
            "medical_history": "Updated2",
            "version": doctor_seen_version,  # stale!
        },
        headers=headers_doctor,
    )
    assert update2.status_code == 409
    assert "modified by another user" in update2.json()["detail"]