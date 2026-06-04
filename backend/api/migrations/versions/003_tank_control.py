"""Tabela tank_control para controle de temperatura por panela (Fase 2)

Revision ID: 003
Revises: 002
Create Date: 2026-06-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tank_control",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tank_id", sa.Integer(), nullable=False),
        sa.Column("setpoint", sa.Float(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="idle"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tank_id"),
    )
    op.create_index(op.f("ix_tank_control_id"), "tank_control", ["id"], unique=False)
    op.create_index(op.f("ix_tank_control_tank_id"), "tank_control", ["tank_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_tank_control_tank_id"), table_name="tank_control")
    op.drop_index(op.f("ix_tank_control_id"), table_name="tank_control")
    op.drop_table("tank_control")
