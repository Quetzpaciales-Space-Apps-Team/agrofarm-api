"""Authenticated in-memory photo forwarding. No fixture or generative fallback."""

import json
import math
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, Protocol

from core_api.domain.problem import ProblemError

CLASSES = {"common_rust", "corn_leaf_blight", "gray_leaf_spot", "healthy", "insect_damage"}


class LeafClient(Protocol):
    def assess(self, data: bytes, content_type: str) -> dict[str, Any]: ...


def validate_assessment(result: Any) -> dict[str, Any]:
    try:
        scores = result["scores"]
        candidate = result["candidate"]
        valid = (
            result["needs_local_review"] is True
            and result["guidance"]["status"] == "needs_local_review"
            and result["limits"]
            and result["score_interpretation"]
            and result["provenance"]["model_version"]
            and set(scores) == CLASSES
            and all(
                isinstance(v, int | float) and math.isfinite(v) and 0 <= v <= 1
                for v in scores.values()
            )
            and abs(sum(scores.values()) - 1) < 1e-4
            and (
                (result["assessment"] == "uncertain" and candidate is None)
                or (
                    result["assessment"] == "possible_condition"
                    and candidate in CLASSES
                    and candidate == max(scores, key=scores.get)
                )
            )
        )
    except (KeyError, TypeError, AttributeError, ValueError):
        valid = False
    if not valid:
        raise ProblemError(502, "invalid_ml_response", "Invalid leaf assessment response")
    parsed: dict[str, Any] = result
    return parsed


class HttpLeafClient:
    def __init__(
        self,
        base_url: str,
        *,
        token_provider: Callable[[], str] | None = None,
        request_id: str = "",
        timeout: float = 15,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token_provider = token_provider
        self.request_id = request_id
        self.timeout = timeout

    def assess(self, data: bytes, content_type: str) -> dict[str, Any]:
        try:
            headers = {"Content-Type": content_type, "X-Request-Id": self.request_id}
            if self.token_provider:
                headers["Authorization"] = f"Bearer {self.token_provider()}"
            request = urllib.request.Request(  # noqa: S310 -- configured service URL
                self.base_url + "/v1/leaves/assess", data=data, headers=headers, method="POST"
            )
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                # Bound the response as well as the uploaded image. Never log its body.
                raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ProblemError(502, "invalid_ml_response", "Oversized leaf assessment response")
            return validate_assessment(json.loads(raw))
        except urllib.error.HTTPError as exc:
            status = exc.code if exc.code in {400, 413, 415} else 503
            raise ProblemError(
                status, "leaf_assessment_failed", "Leaf assessment unavailable or image rejected"
            ) from exc
        except (OSError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProblemError(
                503, "service_unavailable", "Leaf classifier is currently unavailable"
            ) from exc
