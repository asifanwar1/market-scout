from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

WRITE_INTENT = "sqlite_write_intent"

BUSY_TIMEOUT_MS = 15000


def build_engine(url: str) -> Engine:
    engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _configure_sqlite_connection(dbapi_connection, _connection_record):
            dbapi_connection.isolation_level = None
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
            cursor.close()

        @event.listens_for(engine, "begin")
        def _begin(connection):
            immediate = connection.get_execution_options().get(WRITE_INTENT)
            connection.exec_driver_sql("BEGIN IMMEDIATE" if immediate else "BEGIN")

    return engine


def make_sessionmakers(engine: Engine):
    write_engine = engine.execution_options(**{WRITE_INTENT: True})
    return (
        sessionmaker(autocommit=False, autoflush=False, bind=engine),
        sessionmaker(autocommit=False, autoflush=False, bind=write_engine),
        sessionmaker(autocommit=False, autoflush=False, bind=write_engine, expire_on_commit=False),
    )


engine = build_engine(settings.DATABASE_URL)
SessionLocal, WriteSessionLocal, WorkerSessionLocal = make_sessionmakers(engine)
Base = declarative_base()
