import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# 1. PATH RESOLUTION: Force Python to recognize the 'app' module from the root directory
sys.path.append(str(Path(__file__).resolve().parent.parent))

# 2. IMPORT THE VAULT: Pull in your Pydantic settings and SQLAlchemy Base
from app.config import settings
from app.models import Base

config = context.config

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 3. DYNAMIC OVERRIDE: Inject the secure, Pydantic-validated Database URL
config.set_main_option("sqlalchemy.url", settings.ASYNC_DATABASE_URL)

# 4. METADATA ANCHOR: Tell Alembic what models to look at
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()