"""Auth repository for users and refresh tokens."""

import uuid
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import DateTime, ForeignKey, String, select, update
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from core_api.domain.auth import RefreshTokenRecord, UserRecord
from core_api.domain.problem import ProblemError


class _Base(DeclarativeBase):
    pass


class UserRow(_Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RefreshTokenRow(_Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuthRepository(Protocol):
    def create_user(
        self, *, email: str, name: str, role: str, password_hash: str
    ) -> UserRecord: ...

    def get_user_by_email(self, email: str) -> UserRecord | None: ...

    def get_user_by_id(self, user_id: uuid.UUID) -> UserRecord | None: ...

    def update_password_hash(self, user_id: uuid.UUID, password_hash: str) -> None: ...

    def revoke_user_refresh_tokens(self, user_id: uuid.UUID) -> None: ...

    def create_refresh_token(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> RefreshTokenRecord: ...

    def get_refresh_token(self, token_hash: str) -> RefreshTokenRecord | None: ...

    def revoke_refresh_token(self, token_hash: str) -> None: ...


def _to_user(row: UserRow) -> UserRecord:
    return UserRecord(
        id=row.id,
        email=row.email,
        name=row.name,
        role=row.role,
        password_hash=row.password_hash,
        created_at=row.created_at,
    )


def _to_token(row: RefreshTokenRow) -> RefreshTokenRecord:
    return RefreshTokenRecord(
        id=row.id,
        user_id=row.user_id,
        token_hash=row.token_hash,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
    )


class SqlAlchemyAuthRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_user(self, *, email: str, name: str, role: str, password_hash: str) -> UserRecord:
        row = UserRow(
            id=uuid.uuid4(),
            email=email.lower(),
            name=name,
            role=role,
            password_hash=password_hash,
            created_at=datetime.now(UTC),
        )
        with Session(self._engine) as session:
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise ProblemError(409, "conflict", "Email already registered") from exc
            session.refresh(row)
            return _to_user(row)

    def get_user_by_email(self, email: str) -> UserRecord | None:
        with Session(self._engine) as session:
            row = session.scalar(select(UserRow).where(UserRow.email == email.lower()))
            return _to_user(row) if row else None

    def get_user_by_id(self, user_id: uuid.UUID) -> UserRecord | None:
        with Session(self._engine) as session:
            row = session.get(UserRow, user_id)
            return _to_user(row) if row else None

    def update_password_hash(self, user_id: uuid.UUID, password_hash: str) -> None:
        with Session(self._engine) as session:
            row = session.get(UserRow, user_id)
            if row is not None:
                row.password_hash = password_hash
                session.commit()

    def revoke_user_refresh_tokens(self, user_id: uuid.UUID) -> None:
        with Session(self._engine) as session:
            session.execute(
                update(RefreshTokenRow)
                .where(RefreshTokenRow.user_id == user_id, RefreshTokenRow.revoked_at.is_(None))
                .values(revoked_at=datetime.now(UTC))
            )
            session.commit()

    def create_refresh_token(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> RefreshTokenRecord:
        row = RefreshTokenRow(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
            created_at=datetime.now(UTC),
        )
        with Session(self._engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            return _to_token(row)

    def get_refresh_token(self, token_hash: str) -> RefreshTokenRecord | None:
        with Session(self._engine) as session:
            row = session.scalar(
                select(RefreshTokenRow).where(RefreshTokenRow.token_hash == token_hash)
            )
            return _to_token(row) if row else None

    def revoke_refresh_token(self, token_hash: str) -> None:
        with Session(self._engine) as session:
            row = session.scalar(
                select(RefreshTokenRow).where(RefreshTokenRow.token_hash == token_hash)
            )
            if row and row.revoked_at is None:
                row.revoked_at = datetime.now(UTC)
                session.commit()
