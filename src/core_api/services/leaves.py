"""Farm-scoped image screening without retaining uploaded photos."""

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from core_api.clients.leaves import LeafClient, validate_assessment
from core_api.domain.auth import CurrentUser
from core_api.domain.recommendations import DISCLAIMER_TEXT
from core_api.services.farms import FarmService


class LeafAssessmentService:
    def __init__(self, farms: FarmService, client: LeafClient) -> None:
        self.farms = farms
        self.client = client

    def assess(
        self, user: CurrentUser, farm_id: uuid.UUID, data: bytes, content_type: str
    ) -> dict[str, Any]:
        self.farms.get_farm(user, farm_id)
        result = validate_assessment(self.client.assess(data, content_type))
        result["disclaimer"] = DISCLAIMER_TEXT
        result["provenance"] = {
            **result["provenance"],
            "model_name": "maize-leaf-condition-screening",
            "input_hash": hashlib.sha256(data).hexdigest(),
            "generated_at": datetime.now(UTC).isoformat(),
        }
        return result
