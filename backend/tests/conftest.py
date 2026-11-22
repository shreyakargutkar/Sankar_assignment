import os

os.environ["DISABLE_SCHEDULER"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.services.gmail_service import gmail_service
from app.services.google_sheets import google_sheets_service

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_influencers.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def isolate_google_sheets_export(monkeypatch, tmp_path):
    monkeypatch.setattr(
        google_sheets_service,
        "_local_export_file",
        lambda: str(tmp_path / "google_sheets_synced_export.csv"),
    )
    monkeypatch.setattr(
        gmail_service,
        "_simulated_outbox_file",
        lambda: str(tmp_path / "simulated_gmail_outbox.jsonl"),
    )


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
