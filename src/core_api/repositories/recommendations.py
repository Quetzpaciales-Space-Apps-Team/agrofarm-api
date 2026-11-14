"""Repository for persisted farm recommendations and provenance."""

import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from core_api.domain.recommendations import RecommendationRecord


class _Base(DeclarativeBase):
    pass


class FarmRecommendationRow(_Base):
    __tablename__ = "farm_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    farm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    data_versions: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RecommendationRepository(Protocol):
    def save(
        self,
        *,
        rec_id: uuid.UUID,
        farm_id: uuid.UUID,
        model_version: str,
        data_versions: dict[str, str],
        input_hash: str,
        payload: dict[str, Any],
    ) -> RecommendationRecord: ...


class SqlAlchemyRecommendationRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(
        self,
        *,
        rec_id: uuid.UUID,
        farm_id: uuid.UUID,
        model_version: str,
        data_versions: dict[str, str],
        input_hash: str,
        payload: dict[str, Any],
    ) -> RecommendationRecord:
        now = datetime.now(UTC)
        row = FarmRecommendationRow(
            id=rec_id,
            farm_id=farm_id,
            model_version=model_version,
            data_versions=data_versions,
            input_hash=input_hash,
            payload=payload,
            created_at=now,
        )
        with Session(self._engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            return RecommendationRecord(
                id=row.id,
                farm_id=row.farm_id,
                model_version=row.model_version,
                data_versions=row.data_versions,
                input_hash=row.input_hash,
                payload=row.payload,
                created_at=row.created_at,
            )
