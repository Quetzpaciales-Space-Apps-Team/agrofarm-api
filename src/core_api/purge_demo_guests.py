"""Purge expired ephemeral demo guest users and their cloned farms."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from core_api.config import Settings
from core_api.repositories.auth import UserRow
from core_api.repositories.database import create_db_engine
from core_api.repositories.farms import FarmRow

logger = logging.getLogger(__name__)


def purge_demo_guests(*, database_url: str | None = None, max_age_hours: int = 24) -> int:
    """Delete demo-guest-*@demo.agrofarm.invalid users older than max_age_hours."""
    url = database_url or Settings().database_url.get_secret_value()
    engine = create_db_engine(url)
    cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)

    with Session(engine) as session:
        user_ids = list(
            session.scalars(
                select(UserRow.id).where(
                    UserRow.email.like("demo-guest-%@demo.agrofarm.invalid"),
                    UserRow.created_at < cutoff,
                )
            )
        )
        if not user_ids:
            return 0
        session.execute(delete(FarmRow).where(FarmRow.owner_id.in_(user_ids)))
        session.execute(delete(UserRow).where(UserRow.id.in_(user_ids)))
        session.commit()
        return len(user_ids)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    removed = purge_demo_guests()
    logger.info("Purged %d expired demo guest account(s).", removed)
