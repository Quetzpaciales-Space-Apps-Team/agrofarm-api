"""Farm and farmer priorities repository (PostgreSQL + protocol for unit fakes)."""

import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import DateTime, Float, ForeignKey, String, delete, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from core_api.domain.farms import FarmRecord


class _Base(DeclarativeBase):
    pass


class FarmRow(_Base):
    __tablename__ = "farms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    boundary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    area_ha: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_lat: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_lon: Mapped[float] = mapped_column(Float, nullable=False)
    current_rotation: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FarmPrioritiesRow(_Base):
    __tablename__ = "farm_priorities"

    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.id", ondelete="CASCADE"), primary_key=True
    )
    weights: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FarmRepository(Protocol):
    def list_by_owner(
        self, owner_id: uuid.UUID, limit: int, cursor: str | None
    ) -> tuple[list[FarmRecord], str | None]: ...

    def create(
        self,
        *,
        owner_id: uuid.UUID,
        name: str,
        boundary: dict[str, Any],
        area_ha: float,
        centroid_lat: float,
        centroid_lon: float,
        current_rotation: list[str],
    ) -> FarmRecord: ...

    def get(self, farm_id: uuid.UUID) -> FarmRecord | None: ...

    def update(
        self,
        farm_id: uuid.UUID,
        *,
        name: str | None,
        boundary: dict[str, Any] | None,
        area_ha: float | None,
        centroid_lat: float | None,
        centroid_lon: float | None,
        current_rotation: list[str] | None,
    ) -> FarmRecord | None: ...

    def delete(self, farm_id: uuid.UUID) -> bool: ...

    def get_priorities(self, farm_id: uuid.UUID) -> dict[str, Any] | None: ...

    def put_priorities(
        self, farm_id: uuid.UUID, weights: dict[str, float], constraints: dict[str, Any]
    ) -> dict[str, Any]: ...


def _to_record(row: FarmRow) -> FarmRecord:
    return FarmRecord(
        id=row.id,
        owner_id=row.owner_id,
        name=row.name,
        boundary=row.boundary,
        area_ha=row.area_ha,
        centroid_lat=row.centroid_lat,
        centroid_lon=row.centroid_lon,
        current_rotation=list(row.current_rotation),
        created_at=row.created_at,
    )


class SqlAlchemyFarmRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def list_by_owner(
        self, owner_id: uuid.UUID, limit: int, cursor: str | None
    ) -> tuple[list[FarmRecord], str | None]:
        offset = int(cursor) if cursor and cursor.isdigit() else 0
        with Session(self._engine) as session:
            stmt = (
                select(FarmRow)
                .where(FarmRow.owner_id == owner_id)
                .order_by(FarmRow.created_at.desc(), FarmRow.id.asc())
                .offset(offset)
                .limit(limit + 1)
            )
            rows = list(session.scalars(stmt))
        has_more = len(rows) > limit
        items = [_to_record(r) for r in rows[:limit]]
        next_cursor = str(offset + limit) if has_more else None
        return items, next_cursor

    def create(
        self,
        *,
        owner_id: uuid.UUID,
        name: str,
        boundary: dict[str, Any],
        area_ha: float,
        centroid_lat: float,
        centroid_lon: float,
        current_rotation: list[str],
    ) -> FarmRecord:
        row = FarmRow(
            id=uuid.uuid4(),
            owner_id=owner_id,
            name=name,
            boundary=boundary,
            area_ha=area_ha,
            centroid_lat=centroid_lat,
            centroid_lon=centroid_lon,
            current_rotation=current_rotation,
            created_at=datetime.now(UTC),
        )
        with Session(self._engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            return _to_record(row)

    def get(self, farm_id: uuid.UUID) -> FarmRecord | None:
        with Session(self._engine) as session:
            row = session.get(FarmRow, farm_id)
            return _to_record(row) if row else None

    def update(
        self,
        farm_id: uuid.UUID,
        *,
        name: str | None,
        boundary: dict[str, Any] | None,
        area_ha: float | None,
        centroid_lat: float | None,
        centroid_lon: float | None,
        current_rotation: list[str] | None,
    ) -> FarmRecord | None:
        with Session(self._engine) as session:
            row = session.get(FarmRow, farm_id)
            if not row:
                return None
            if name is not None:
                row.name = name
            if boundary is not None:
                row.boundary = boundary
            if area_ha is not None:
                row.area_ha = area_ha
            if centroid_lat is not None:
                row.centroid_lat = centroid_lat
            if centroid_lon is not None:
                row.centroid_lon = centroid_lon
            if current_rotation is not None:
                row.current_rotation = current_rotation
            session.commit()
            session.refresh(row)
            return _to_record(row)

    def delete(self, farm_id: uuid.UUID) -> bool:
        with Session(self._engine) as session:
            result = session.execute(delete(FarmRow).where(FarmRow.id == farm_id))
            session.commit()
            return bool(result.rowcount)  # type: ignore[attr-defined]

    def get_priorities(self, farm_id: uuid.UUID) -> dict[str, Any] | None:
        with Session(self._engine) as session:
            row = session.get(FarmPrioritiesRow, farm_id)
            if not row:
                return None
            return {"weights": row.weights, "constraints": row.constraints}

    def put_priorities(
        self, farm_id: uuid.UUID, weights: dict[str, float], constraints: dict[str, Any]
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        with Session(self._engine) as session:
            row = session.get(FarmPrioritiesRow, farm_id)
            if row is None:
                row = FarmPrioritiesRow(
                    farm_id=farm_id,
                    weights=weights,
                    constraints=constraints,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.weights = weights
                row.constraints = constraints
                row.updated_at = now
            session.commit()
            return {"weights": row.weights, "constraints": row.constraints}
