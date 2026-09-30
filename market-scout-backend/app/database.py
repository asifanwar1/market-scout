from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# check_same_thread=False: the background run worker (added later) uses its own
# sessions from another thread.
connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

if settings.is_sqlite:
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
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    @event.listens_for(engine, "begin")
    def _begin(connection):
        connection.exec_driver_sql("BEGIN")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
