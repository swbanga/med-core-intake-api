# tests/test_idor.py
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_idor_prevention_matrix(async_client: AsyncClient, seeded_role: str, db_session):
    """
    Proves that Patient A cannot read Patient B's medical history, 
    but a legally authorized Doctor CAN read Patient B's history.
    """
    
    # ==========================================
    # 1. ARRANGE: FORGE THE IDENTITIES
    # ==========================================
    # We need a Doctor role for the final check
    from app.models import Role
    import uuid
    doctor_role_id = str(uuid.uuid4())
    doctor_role = Role(id=doctor_role_id, name="Doctor", description="Medical Staff")
    db_session.add(doctor_role)
    await db_session.commit()

    password = "SecurePassword123!"
    
    # Register Malicious Patient (Attacker)
    await async_client.post("/v1/identity/users", json={"email": "attacker@matrix.com", "password": password, "role_id": seeded_role})
    
    # Register Victim Patient
    await async_client.post("/v1/identity/users", json={"email": "victim@matrix.com", "password": password, "role_id": seeded_role})
    
    # Register Doctor (Authorized)
    await async_client.post("/v1/identity/users", json={"email": "doc@matrix.com", "password": password, "role_id": doctor_role_id})

    # ==========================================
    # 2. ARRANGE: EXTRACT THE TOKENS
    # ==========================================
    # Get Attacker Token
    res_att = await async_client.post("/login", data={"username": "attacker@matrix.com", "password": password})
    attacker_token = res_att.json()["access_token"]
    
    # Get Victim Token
    res_vic = await async_client.post("/login", data={"username": "victim@matrix.com", "password": password})
    victim_token = res_vic.json()["access_token"]

    # Get Doctor Token
    res_doc = await async_client.post("/login", data={"username": "doc@matrix.com", "password": password})
    doctor_token = res_doc.json()["access_token"]

    # ==========================================
    # 3. ACT & ASSERT: THE VICTIM CREATES DATA
    # ==========================================
    # Victim creates their profile
    headers_victim = {"Authorization": f"Bearer {victim_token}"}
    profile_payload = {
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1980-01-01",
        "medical_history": "Allergic to Penicillin"
    }
    create_res = await async_client.post("/v1/patients/profile", json=profile_payload, headers=headers_victim)
    assert create_res.status_code == 201
    profile_id = create_res.json()["id"]

    # ==========================================
    # 4. ACT & ASSERT: THE IDOR ATTACK
    # ==========================================
    # Attacker tries to GET the Victim's profile using the Victim's profile_id
    headers_attacker = {"Authorization": f"Bearer {attacker_token}"}
    attack_res = await async_client.get(f"/v1/patients/profile/{profile_id}", headers=headers_attacker)
    
    # MATHEMATICAL PROOF: The system must violently reject the attacker
    assert attack_res.status_code == 403
    assert attack_res.json()["detail"] == "Not enough permissions"

    # ==========================================
    # 5. ACT & ASSERT: THE AUTHORIZED ACCESS
    # ==========================================
    # Doctor tries to GET the Victim's profile
    headers_doctor = {"Authorization": f"Bearer {doctor_token}"}
    doc_res = await async_client.get(f"/v1/patients/profile/{profile_id}", headers=headers_doctor)
    
    # MATHEMATICAL PROOF: The system must allow the doctor
    assert doc_res.status_code == 200
    assert doc_res.json()["first_name"] == "John"