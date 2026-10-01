from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# Execution option that marks an engine's transactions as "may write".
WRITE_INTENT = "sqlite_write_intent"

# SQLite allows many readers but one writer. A transaction that starts by *reading* and later
# *writes* fails at once with "database is locked" if anyone else committed in between (its snapshot
# is stale), however long the busy timeout is. That is what a background run does all the time (read,
# wait on the network, write) while people edit leads. So every transaction that may write takes the
# write lock up front (BEGIN IMMEDIATE) and then waits its turn properly; read-only ones stay plain
# so they never queue. Keep write transactions short, and never hold one across a network call.
BUSY_TIMEOUT_MS = 15000


def build_engine(url: str) -> Engine:
    # check_same_thread=False: the background worker and sync threads use their own sessions.
    engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _configure_sqlite_connection(dbapi_connection, _connection_record):
            # pysqlite's default transaction handling breaks SAVEPOINT; take control of
            # BEGIN ourselves (SQLAlchemy's documented workaround, see _begin below).
            dbapi_connection.isolation_level = None
            cursor = dbapi_connection.cursor()
            # WAL lets the UI read while a run is writing; without foreign_keys=ON SQLite
            # silently ignores every FK constraint.
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
    """(read, write, worker) session factories over one engine. The write ones lock up front; the
    worker's also keeps loaded objects after a commit, so reading an attribute never silently opens a
    new transaction (and its lock) in the middle of a network call."""
    write_engine = engine.execution_options(**{WRITE_INTENT: True})
    return (
        sessionmaker(autocommit=False, autoflush=False, bind=engine),
        sessionmaker(autocommit=False, autoflush=False, bind=write_engine),
        sessionmaker(autocommit=False, autoflush=False, bind=write_engine, expire_on_commit=False),
    )


engine = build_engine(settings.DATABASE_URL)
SessionLocal, WriteSessionLocal, WorkerSessionLocal = make_sessionmakers(engine)
Base = declarative_base()
