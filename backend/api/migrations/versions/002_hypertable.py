"""Converter tabela readings em hypertable TimescaleDB

Revision ID: 002
Revises: 001
Create Date: 2026-05-19

"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "SELECT create_hypertable('readings', 'recorded_at', if_not_exists => TRUE)"
    )


def downgrade() -> None:
    # Não é possível desfazer a conversão para hypertable de forma simples.
    # Para reverter: recriar a tabela sem a extensão TimescaleDB.
    pass
