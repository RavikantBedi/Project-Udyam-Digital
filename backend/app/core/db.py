import os
from sqlmodel import SQLModel, create_engine, Session
from app.core.config import get_settings

settings = get_settings()

# Ensure db directory exists
db_path = settings.database_url.replace("sqlite:///", "")
db_dir = os.path.dirname(db_path)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db():
    from app.models import models  # noqa: F401 — ensure models are registered
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
