import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

# Expect a PostgreSQL connection URL via environment variable with asyncpg
# E.g., postgresql+asyncpg://user:password@localhost:5432/pulsus
# We provide a local sqlite fallback for initial testing if needed, though async sqlite uses aiosqlite.
# Since the requirement is PostgreSQL, we will default to postgresql+asyncpg schema.

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/pulsus"
)

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with async_session() as session:
        yield session
