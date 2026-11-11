"""Database engine, session, and declarative base.

SQLite is used for the local prototype. A PostgreSQL migration path is
documented in docs/ARCHITECTURE.md (D-003).
"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.app_debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Yield a database session and ensure it is closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_MIGRATION_COLUMNS: dict[str, dict[str, str]] = {
    "sellers": {
        "growth_vs_margin_priority": "VARCHAR NOT NULL DEFAULT 'balanced'",
        "supplier_relationship_strength": "VARCHAR NOT NULL DEFAULT 'standard'",
        "max_credit_stretch_pct": "FLOAT NOT NULL DEFAULT 0.0",
    },
    "products": {
        "seasonality_tag": "VARCHAR",
        "demand_segment": "VARCHAR NOT NULL DEFAULT 'discretionary'",
        "is_festival_sensitive": "BOOLEAN NOT NULL DEFAULT 0",
        "is_payday_sensitive": "BOOLEAN NOT NULL DEFAULT 0",
        "is_wedding_sensitive": "BOOLEAN NOT NULL DEFAULT 0",
        "product_attributes": "TEXT",
    },
    "recommendations": {
        "action_type": "VARCHAR",
        "outcome_status": "VARCHAR NOT NULL DEFAULT 'pending'",
        "outcome_notes": "TEXT",
        "actual_units_ordered": "INTEGER",
        "actual_revenue_delta_pct": "FLOAT",
        "actual_margin_pct": "FLOAT",
        "outcome_recorded_at": "DATETIME",
    },
}


def ensure_schema_columns(target_engine=None) -> None:
    """Idempotently add newly introduced columns on existing SQLite databases."""
    eng = target_engine or engine
    inspector = inspect(eng)
    existing_tables = set(inspector.get_table_names())
    with eng.begin() as conn:
        for table_name, columns in _MIGRATION_COLUMNS.items():
            if table_name not in existing_tables:
                continue
            present = {col["name"] for col in inspector.get_columns(table_name)}
            for col_name, ddl in columns.items():
                if col_name not in present:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {ddl}"))


def create_db_and_tables():
    """Create all tables defined on the declarative base and apply safe additive migrations."""
    Base.metadata.create_all(bind=engine)
    ensure_schema_columns(engine)
