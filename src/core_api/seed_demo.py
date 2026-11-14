"""Idempotent CLI seeder for a deterministic demo user, farm, priorities, and recommendation."""

import logging
import uuid
from typing import Any

from core_api.clients.demo import DemoMLClient
from core_api.config import Settings
from core_api.domain.auth import hash_password
from core_api.domain.farms import default_priorities
from core_api.domain.recommendations import compute_input_hash
from core_api.repositories.auth import SqlAlchemyAuthRepository
from core_api.repositories.database import create_db_engine
from core_api.repositories.farms import SqlAlchemyFarmRepository
from core_api.repositories.recommendations import SqlAlchemyRecommendationRepository

logger = logging.getLogger(__name__)

DEMO_USER_EMAIL = "demo@agrofarm.org"
DEMO_USER_NAME = "Guatemala Pilot Farmer"
DEMO_USER_PASSWORD = "DemoPass2026!"  # noqa: S105
DEMO_FARM_NAME = "Guatemala Pilot Farm (Provisional)"
DEMO_FARM_BOUNDARY: dict[str, Any] = {
    "type": "Polygon",
    "coordinates": [
        [
            [-90.5150, 14.6330],
            [-90.5110, 14.6330],
            [-90.5110, 14.6370],
            [-90.5150, 14.6370],
            [-90.5150, 14.6330],
        ]
    ],
}


def seed_demo(database_url: str | None = None) -> dict[str, str]:
    """Ensure demo user, provisional Guatemala farm, priorities, and recommendation exist."""
    url = database_url or Settings().database_url.get_secret_value()
    engine = create_db_engine(url)

    auth_repo = SqlAlchemyAuthRepository(engine)
    farm_repo = SqlAlchemyFarmRepository(engine)
    rec_repo = SqlAlchemyRecommendationRepository(engine)

    user = auth_repo.get_user_by_email(DEMO_USER_EMAIL)
    if user is None:
        user = auth_repo.create_user(
            email=DEMO_USER_EMAIL,
            name=DEMO_USER_NAME,
            role="farmer",
            password_hash=hash_password(DEMO_USER_PASSWORD),
        )

    farms, _ = farm_repo.list_by_owner(user.id, limit=50, cursor=None)
    farm = next((f for f in farms if f.name == DEMO_FARM_NAME), None)
    if farm is None:
        farm = farm_repo.create(
            owner_id=user.id,
            name=DEMO_FARM_NAME,
            boundary=DEMO_FARM_BOUNDARY,
            area_ha=12.5,
            centroid_lat=14.635,
            centroid_lon=-90.513,
            current_rotation=["maize", "fallow"],
        )

    defaults = default_priorities()
    farm_repo.put_priorities(
        farm.id,
        weights=defaults["weights"],
        constraints=defaults["constraints"],
    )

    rec_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"agrofarm-demo-rec:{farm.id}")
    if rec_repo.get(rec_id) is None:
        snapshot = DemoMLClient().score_rotations({"farm_id": str(farm.id)})
        provenance = snapshot.get("provenance", {})
        rec_payload = {
            "recommendation_id": str(rec_id),
            "farm_id": str(farm.id),
            "disclaimer": snapshot["disclaimer"],
            "strategies": snapshot["strategies"],
            "provenance": provenance,
        }
        rec_repo.save(
            rec_id=rec_id,
            farm_id=farm.id,
            model_version=str(provenance.get("model_version", "cached_demo-0.1.0")),
            data_versions={
                str(k): str(v) for k, v in dict(provenance.get("data_versions", {})).items()
            },
            input_hash=compute_input_hash({"farm_id": str(farm.id), "demo": True}),
            payload=rec_payload,
        )

    return {
        "user_id": str(user.id),
        "farm_id": str(farm.id),
        "recommendation_id": str(rec_id),
    }


def main() -> None:
    logging.basicConfig(level="INFO", format="%(message)s")
    ids = seed_demo()
    logger.info(
        "Demo data ready: user_id=%s farm_id=%s recommendation_id=%s",
        ids["user_id"],
        ids["farm_id"],
        ids["recommendation_id"],
    )


if __name__ == "__main__":
    main()
