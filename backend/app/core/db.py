"""Database engine, session, and init — PostgreSQL in prod, SQLite for tests."""
import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()

# Use SQLite override for tests if DATABASE_TEST_URL is set
_db_url = os.getenv("DATABASE_TEST_URL") or settings.database_url
_connect_args: dict = {}
if _db_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    _db_url,
    echo=False,
    connect_args=_connect_args,
)


def init_db() -> None:
    """Create all tables (dev only — use Alembic migrations in production)."""
    from app.models import models  # noqa: F401 — ensure models registered
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager for transactional session usage in scripts/jobs."""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
