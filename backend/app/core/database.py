from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_schema():
    """Add new columns to existing SQLite tables without dropping data."""
    if "sqlite" not in settings.DATABASE_URL:
        return
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if "influencers" in tables:
        existing = {c["name"] for c in inspector.get_columns("influencers")}
        statements = []
        if "opted_out" not in existing:
            statements.append("ALTER TABLE influencers ADD COLUMN opted_out BOOLEAN DEFAULT 0")
        if "last_contacted_at" not in existing:
            statements.append("ALTER TABLE influencers ADD COLUMN last_contacted_at DATETIME")
        if statements:
            with engine.begin() as conn:
                for stmt in statements:
                    conn.execute(text(stmt))

    if "daily_send_quotas" in tables:
        quota_columns = {c["name"] for c in inspector.get_columns("daily_send_quotas")}
        if "reserved" not in quota_columns:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE daily_send_quotas ADD COLUMN reserved INTEGER NOT NULL DEFAULT 0")
                )
