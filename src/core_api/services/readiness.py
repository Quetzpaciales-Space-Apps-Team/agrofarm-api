"""Use case: are the dependencies this service needs reachable?"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class Probe(Protocol):
    name: str

    def ping(self) -> bool: ...


@dataclass(frozen=True)
class ReadinessReport:
    ready: bool
    checks: dict[str, str]


class ReadinessService:
    def __init__(self, probes: Sequence[Probe]) -> None:
        self._probes = probes

    def check(self) -> ReadinessReport:
        checks = {probe.name: "ok" if probe.ping() else "failed" for probe in self._probes}
        return ReadinessReport(ready=all(v == "ok" for v in checks.values()), checks=checks)
