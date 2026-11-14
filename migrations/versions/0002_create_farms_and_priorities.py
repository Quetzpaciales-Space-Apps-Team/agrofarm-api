"""Create farms and farm_priorities tables (BE-020, BE-025).

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "farms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("boundary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("area_ha", sa.Float(), nullable=False),
        sa.Column("centroid_lat", sa.Float(), nullable=False),
        sa.Column("centroid_lon", sa.Float(), nullable=False),
        sa.Column(
            "current_rotation",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "farm_priorities",
        sa.Column(
            "farm_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("farms.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("weights", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("farm_priorities")
    op.drop_table("farms")
