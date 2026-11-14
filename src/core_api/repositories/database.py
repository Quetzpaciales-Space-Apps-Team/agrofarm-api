"""Database access. Only this layer knows about SQLAlchemy."""

import logging

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def create_db_engine(url: str, connect_timeout: int = 5) -> Engine:
    # The engine connects lazily, so building it never fails at startup.
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": connect_timeout})


class DatabaseProbe:
    name = "database"

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def ping(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            # The error class is enough to diagnose. The message can contain the DSN.
            logger.warning("database probe failed: %s", type(error).__name__)
            return False
        return True
