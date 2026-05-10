import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
import redis.asyncio as redis
import uuid
import bcrypt
from fastapi_limiter import FastAPILimiter

from app.main import app
from app.database import get_db_session
from app.models import Base, Role, User
from app.config import settings

# ------------------------------------------------------------------
# DATABASE ENGINE
# ------------------------------------------------------------------
engine = create_async_engine(
    settings.TEST_DATABASE_URL,
    poolclass=NullPool,
    echo=False
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        app.dependency_overrides[get_db_session] = lambda: session
        yield session
        app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def clean_redis():
    """Replace all Redis references with a fresh test instance."""
    test_redis = redis.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )
    await test_redis.flushdb()

    # Overwrite every module that holds a direct reference
    import app.cache as cache_module
    import app.oauth2 as oauth2_module
    import app.routers.auth as auth_router
    import app.main as main_module

    cache_module.redis_client = test_redis
    oauth2_module.redis_client = test_redis # type: ignore
    auth_router.redis_client = test_redis # type: ignore
    main_module.redis_client = test_redis

    # Initialise the rate limiter AFTER setting the new client
    await FastAPILimiter.init(test_redis)

    yield test_redis

    # Tear down
    await test_redis.aclose()


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session, clean_redis):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# ------------------------------------------------------------------
# SEEDED ROLES
# ------------------------------------------------------------------
@pytest_asyncio.fixture(scope="function")
async def seeded_roles(db_session):
    roles = {
        "System_Admin": Role(id=uuid.uuid4(), name="System_Admin", description="Admin"),
        "Doctor": Role(id=uuid.uuid4(), name="Doctor", description="MD"),
        "Patient": Role(id=uuid.uuid4(), name="Patient", description="Patient"),
        "Auditor": Role(id=uuid.uuid4(), name="Auditor", description="Auditor"),
    }
    for r in roles.values():
        db_session.add(r)
    await db_session.commit()
    return {name: str(role.id) for name, role in roles.items()}


# ------------------------------------------------------------------
# USER FIXTURES
# ------------------------------------------------------------------
async def _create_user_in_db(session, email: str, password: str, role_id, is_active=True):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode()
    user = User(
        email=email,
        hashed_password=hashed,
        role_id=role_id,
        is_active=is_active,
        is_password_set=True
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def admin_user(db_session, seeded_roles):
    return await _create_user_in_db(
        db_session, "admin@test.com", "AdminPass123!", seeded_roles["System_Admin"]
    )


@pytest_asyncio.fixture(scope="function")
async def admin_token(async_client, admin_user):
    resp = await async_client.post("/login", data={
        "username": admin_user.email,
        "password": "AdminPass123!"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture(scope="function")
async def doctor_user(db_session, seeded_roles):
    return await _create_user_in_db(
        db_session, "doctor@test.com", "DoctorPass123!", seeded_roles["Doctor"]
    )


@pytest_asyncio.fixture(scope="function")
async def doctor_token(async_client, doctor_user):
    resp = await async_client.post("/login", data={
        "username": doctor_user.email,
        "password": "DoctorPass123!"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture(scope="function")
async def patient_user(db_session, seeded_roles):
    return await _create_user_in_db(
        db_session, "patient@test.com", "PatientPass123!", seeded_roles["Patient"]
    )


@pytest_asyncio.fixture(scope="function")
async def patient_token(async_client, patient_user):
    resp = await async_client.post("/login", data={
        "username": patient_user.email,
        "password": "PatientPass123!"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture(scope="function")
async def second_patient_user(db_session, seeded_roles):
    return await _create_user_in_db(
        db_session, "second_patient@test.com", "SecPatient123!", seeded_roles["Patient"]
    )


@pytest_asyncio.fixture(scope="function")
async def second_patient_token(async_client, second_patient_user):
    resp = await async_client.post("/login", data={
        "username": second_patient_user.email,
        "password": "SecPatient123!"
    })
    return resp.json()["access_token"]


@pytest_asyncio.fixture(scope="function")
async def auditor_user(db_session, seeded_roles):
    return await _create_user_in_db(
        db_session, "auditor@test.com", "AuditorPass123!", seeded_roles["Auditor"]
    )


@pytest_asyncio.fixture(scope="function")
async def auditor_token(async_client, auditor_user):
    resp = await async_client.post("/login", data={
        "username": auditor_user.email,
        "password": "AuditorPass123!"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]