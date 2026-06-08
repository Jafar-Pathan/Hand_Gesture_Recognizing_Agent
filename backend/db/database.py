"""
SQLAlchemy database engine, session, and base model configuration.

Supports both SQLite (``sqlite:///``) and PostgreSQL (``postgresql://``)
connection strings via the ``DATABASE_URL`` setting.
"""

from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.core.config import settings

# ---------------------------------------------------------------------------
# Engine setup
# ---------------------------------------------------------------------------

_connect_args: dict = {}
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite needs check_same_thread=False for FastAPI's thread-per-request model
    _connect_args["check_same_thread"] = False

engine: Engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
    echo=False,
)

# Enable WAL mode and foreign-key enforcement for SQLite
if settings.DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal: sessionmaker[Session] = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------

Base = declarative_base()

# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy session.

    The session is committed on success and rolled back on error, then closed.
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Initialisation helper
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Create all tables that do not yet exist.

    Imports every model module so that the ORM metadata is fully populated
    before ``create_all`` is called.
    """
    # Side-effect imports to register models with Base.metadata
    import backend.models.audit  # noqa: F401
    import backend.models.prediction  # noqa: F401
    import backend.models.training  # noqa: F401
    import backend.models.user  # noqa: F401

    Base.metadata.create_all(bind=engine)
