"""Database access. Only repositories talk to PostgreSQL."""

from sqlalchemy import create_engine, text


class Database:
    def __init__(self, url: str) -> None:
        self._engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 2})

    def ping(self) -> bool:
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            return False
        return True

    def dispose(self) -> None:
        self._engine.dispose()
