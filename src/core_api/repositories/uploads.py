"""Repository for farm uploads and parsed farm observation rows."""

import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import DateTime, ForeignKey, Integer, String, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from core_api.domain.uploads import RowErrorItem, UploadFormat, UploadRecord, UploadStatus


class _Base(DeclarativeBase):
    pass


class FarmUploadRow(_Base):
    __tablename__ = "farm_uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    farm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    rows_total: Mapped[int] = mapped_column(Integer, nullable=False)
    rows_accepted: Mapped[int] = mapped_column(Integer, nullable=False)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    raw_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FarmUploadDataRow(_Base):
    __tablename__ = "farm_upload_rows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farm_uploads.id", ondelete="CASCADE"), nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    row_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class UploadRepository(Protocol):
    def list_by_farm(
        self, farm_id: uuid.UUID, limit: int, cursor: str | None
    ) -> tuple[list[UploadRecord], str | None]: ...

    def create(
        self,
        *,
        upload_id: uuid.UUID,
        farm_id: uuid.UUID,
        filename: str,
        fmt: UploadFormat,
        status: UploadStatus,
        rows_total: int,
        rows_accepted: int,
        errors: list[RowErrorItem],
        raw_path: str,
        accepted_rows: list[dict[str, Any]],
    ) -> UploadRecord: ...


def _to_record(row: FarmUploadRow) -> UploadRecord:
    fmt: UploadFormat = "geojson" if row.format == "geojson" else "csv"
    status: UploadStatus = (
        "accepted"
        if row.status == "accepted"
        else ("accepted_with_errors" if row.status == "accepted_with_errors" else "rejected")
    )
    return UploadRecord(
        id=row.id,
        farm_id=row.farm_id,
        filename=row.filename,
        format=fmt,
        status=status,
        rows_total=row.rows_total,
        rows_accepted=row.rows_accepted,
        errors=[
            RowErrorItem(row=e["row"], column=e.get("column"), message=e["message"])
            for e in row.errors
        ],
        created_at=row.created_at,
    )


class SqlAlchemyUploadRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def list_by_farm(
        self, farm_id: uuid.UUID, limit: int, cursor: str | None
    ) -> tuple[list[UploadRecord], str | None]:
        offset = int(cursor) if cursor and cursor.isdigit() else 0
        with Session(self._engine) as session:
            stmt = (
                select(FarmUploadRow)
                .where(FarmUploadRow.farm_id == farm_id)
                .order_by(FarmUploadRow.created_at.desc(), FarmUploadRow.id.asc())
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
        upload_id: uuid.UUID,
        farm_id: uuid.UUID,
        filename: str,
        fmt: UploadFormat,
        status: UploadStatus,
        rows_total: int,
        rows_accepted: int,
        errors: list[RowErrorItem],
        raw_path: str,
        accepted_rows: list[dict[str, Any]],
    ) -> UploadRecord:
        now = datetime.now(UTC)
        upload_row = FarmUploadRow(
            id=upload_id,
            farm_id=farm_id,
            filename=filename,
            format=fmt,
            status=status,
            rows_total=rows_total,
            rows_accepted=rows_accepted,
            errors=[{"row": e.row, "column": e.column, "message": e.message} for e in errors],
            raw_path=raw_path,
            created_at=now,
        )
        data_rows = [
            FarmUploadDataRow(
                id=uuid.uuid4(),
                upload_id=upload_id,
                farm_id=farm_id,
                row_data=row_data,
            )
            for row_data in accepted_rows
        ]
        with Session(self._engine) as session:
            session.add(upload_row)
            session.flush()
            session.add_all(data_rows)
            session.commit()
            session.refresh(upload_row)
            return _to_record(upload_row)
