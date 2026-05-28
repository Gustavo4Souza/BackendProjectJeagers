"""Schema inicial: users, refresh_tokens, tanks, readings, alerts, yeast_profiles, batches, batch_events

Revision ID: 001
Revises:
Create Date: 2026-05-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("password", sa.String(), nullable=True),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_jti", sa.String(length=80), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_tokens_id"), "refresh_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_refresh_tokens_token_jti"), "refresh_tokens", ["token_jti"], unique=True)
    op.create_index(op.f("ix_refresh_tokens_username"), "refresh_tokens", ["username"], unique=False)

    op.create_table(
        "tanks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("location", sa.String(length=100), nullable=True),
        sa.Column("temp_min", sa.Float(), nullable=False),
        sa.Column("temp_max", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tanks_id"), "tanks", ["id"], unique=False)

    op.create_table(
        "readings",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("tank_id", sa.Integer(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_readings_id"), "readings", ["id"], unique=False)
    op.create_index(op.f("ix_readings_tank_id"), "readings", ["tank_id"], unique=False)
    op.create_index(op.f("ix_readings_recorded_at"), "readings", ["recorded_at"], unique=False)

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tank_id", sa.Integer(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("fired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["acknowledged_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_id"), "alerts", ["id"], unique=False)
    op.create_index(op.f("ix_alerts_tank_id"), "alerts", ["tank_id"], unique=False)

    op.create_table(
        "yeast_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("strain", sa.String(length=120), nullable=True),
        sa.Column("attenuation_min", sa.Float(), nullable=True),
        sa.Column("attenuation_max", sa.Float(), nullable=True),
        sa.Column("temperature_min_c", sa.Float(), nullable=True),
        sa.Column("temperature_max_c", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_yeast_profiles_id"), "yeast_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_yeast_profiles_name"), "yeast_profiles", ["name"], unique=True)

    op.create_table(
        "batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("style", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("fermenter_id", sa.String(length=100), nullable=True),
        sa.Column("yeast_profile_id", sa.Integer(), nullable=True),
        sa.Column("original_gravity", sa.Float(), nullable=True),
        sa.Column("final_gravity", sa.Float(), nullable=True),
        sa.Column("volume_liters", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["yeast_profile_id"], ["yeast_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_batches_fermenter_id"), "batches", ["fermenter_id"], unique=False)
    op.create_index(op.f("ix_batches_id"), "batches", ["id"], unique=False)
    op.create_index(op.f("ix_batches_name"), "batches", ["name"], unique=False)
    op.create_index(op.f("ix_batches_started_at"), "batches", ["started_at"], unique=False)
    op.create_index(op.f("ix_batches_ended_at"), "batches", ["ended_at"], unique=False)
    op.create_index(op.f("ix_batches_status"), "batches", ["status"], unique=False)
    op.create_index(op.f("ix_batches_style"), "batches", ["style"], unique=False)

    op.create_table(
        "batch_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_batch_events_batch_id"), "batch_events", ["batch_id"], unique=False)
    op.create_index(op.f("ix_batch_events_event_type"), "batch_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_batch_events_id"), "batch_events", ["id"], unique=False)
    op.create_index(op.f("ix_batch_events_occurred_at"), "batch_events", ["occurred_at"], unique=False)


def downgrade() -> None:
    op.drop_table("batch_events")
    op.drop_table("batches")
    op.drop_table("yeast_profiles")
    op.drop_table("alerts")
    op.drop_table("readings")
    op.drop_table("tanks")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
