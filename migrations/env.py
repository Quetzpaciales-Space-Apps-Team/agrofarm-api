"""Alembic environment. The database URL comes from the same Settings as the app."""

from alembic import context
from sqlalchemy import create_engine

from core_api.config import Settings

# No ORM models yet. Set this to the models' metadata when the first table lands.
target_metadata = None


def run_migrations() -> None:
    url = Settings().database_url.get_secret_value()
    with create_engine(url).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations()
