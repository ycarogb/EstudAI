from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sqlalchemy import text

from app.config import settings
from app.db.models import Base

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_async_engine(settings.database_url, echo=False, connect_args=connect_args)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if settings.database_url.startswith("sqlite"):
            result = await conn.execute(text("PRAGMA table_info(projects)"))
            columns = {row[1] for row in result.fetchall()}
            if "analysis_data" not in columns:
                await conn.execute(
                    text("ALTER TABLE projects ADD COLUMN analysis_data JSON")
                )
        await conn.run_sync(_migrate_schema)


def _migrate_schema(sync_conn) -> None:
    from sqlalchemy import inspect, text

    insp = inspect(sync_conn)
    if "projects" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("projects")}
        if "analysis_data" not in cols:
            sync_conn.execute(text("ALTER TABLE projects ADD COLUMN analysis_data JSON"))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
