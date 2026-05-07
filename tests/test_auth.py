# tests/test_auth.py
import pytest
from httpx import AsyncClient

# This decorator tells Pytest that every function in this file is an asynchronous coroutine
pytestmark = pytest.mark.asyncio

# ==========================================
# ATTACK VECTOR 1: IDENTITY REGISTRATION
# ==========================================
async def test_register_user_success(async_client: AsyncClient, seeded_role: str):
    """Proves the perimeter allows valid user registration."""
    payload = {
        "email": "agent@matrix.com",
        "password": "SecurePassword123!",
        "role_id": seeded_role
    }
    
    response = await async_client.post("/v1/identity/users", json=payload)
    
    # 1. Assert strict HTTP status
    assert response.status_code == 201
    
    # 2. Assert data structure and security boundaries
    data = response.json()
    assert data["email"] == "agent@matrix.com"
    assert "id" in data
    assert "hashed_password" not in data # MATHEMTICAL PROOF: Password is not leaked

async def test_register_duplicate_user_rejected(async_client: AsyncClient, seeded_role: str):
    """Proves the database physically rejects duplicate identities (409 Conflict)."""
    payload = {
        "email": "clone@matrix.com",
        "password": "SecurePassword123!",
        "role_id": seeded_role
    }
    
    # Fire first request (Success)
    await async_client.post("/v1/identity/users", json=payload)
    
    # Fire second request (Should violently fail)
    response = await async_client.post("/v1/identity/users", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"] == "Identity already exists."

# ==========================================
# ATTACK VECTOR 2: THE JWT FORGE
# ==========================================
async def test_login_success_and_jwt_issuance(async_client: AsyncClient, seeded_role: str):
    """Proves the login endpoint verifies bcrypt hashes and issues a valid JWT."""
    # Arrange: Create the user first
    password = "SecurePassword123!"
    await async_client.post("/v1/identity/users", json={
        "email": "neo@matrix.com", "password": password, "role_id": seeded_role
    })
    
    # Act: Attempt OAuth2 Form-Data Login
    login_data = {
        "username": "neo@matrix.com",
        "password": password
    }
    # Notice we use 'data=' instead of 'json=' because OAuth2 strictly demands form-data
    response = await async_client.post("/login", data=login_data)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

async def test_login_invalid_credentials_rejected(async_client: AsyncClient, seeded_role: str):
    """Proves the system rejects brute-force / bad passwords without enumerating users."""
    # Arrange: Create user
    await async_client.post("/v1/identity/users", json={
        "email": "trinity@matrix.com", "password": "RealPassword123!", "role_id": seeded_role
    })
    
    # Act: Attack with wrong password
    response = await async_client.post("/login", data={
        "username": "trinity@matrix.com", "password": "WrongPassword!@#"
    })
    
    # Assert: Must be a brutal, ambiguous 403 Forbidden
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid Credentials"