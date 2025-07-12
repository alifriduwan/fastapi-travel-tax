import asyncio
from typing import AsyncIterator

from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker

from .user_model import *

connect_args = {"check_same_thread": False}

engine: AsyncEngine = None


async def init_db():
    """Initialize the database engine and create tables."""
    global engine

    engine = create_async_engine(
        "sqlite+aiosqlite:///database.db",
        echo=True,
        future=True,
        connect_args=connect_args,
    )

    await create_db_and_tables()


async def create_db_and_tables():
    """Create database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Get async database session."""
    if engine is None:
        raise Exception("Database engine is not initialized. Call init_db() first.")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


async def close_db():
    """Close database connection."""
    global engine
    if engine is not None:
        await engine.dispose()
        engine = None