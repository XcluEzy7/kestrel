"""Add Shoo accounts, sessions, batch ownership, and profile owner.

Revision ID: x6y7z8a9b0c1
Revises: w5x6y7z8a9b0
Create Date: 2026-09-10 00:00:00.000000

Existing profiles remain unowned. Operators claim them explicitly with
SHOO_CLAIM_LEGACY_DATA=true during first verified login; no migration guesses
which future Shoo identity owns private data.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "x6y7z8a9b0c1"
branch_labels: str | Sequence[str] | None = None
down_revision: str | None = "w5x6y7z8a9b0"
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pairwise_sub", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounts_pairwise_sub", "accounts", ["pairwise_sub"], unique=True)
    with op.batch_alter_table("profiles") as batch_op:
        batch_op.add_column(sa.Column("account_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_profiles_account_id", ["account_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_profiles_account_id_accounts", "accounts", ["account_id"], ["id"], ondelete="SET NULL"
        )
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"], unique=False)
    op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
    op.create_table(
        "auth_batches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=64), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_batch_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_batch_id", name="uq_auth_batch_provider_id"),
    )
    op.create_index("ix_auth_batches_public_id", "auth_batches", ["public_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_auth_batches_public_id", table_name="auth_batches")
    op.drop_table("auth_batches")
    op.drop_index("ix_auth_sessions_token_hash", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    with op.batch_alter_table("profiles") as batch_op:
        batch_op.drop_constraint("fk_profiles_account_id_accounts", type_="foreignkey")
        batch_op.drop_index("ix_profiles_account_id")
        batch_op.drop_column("account_id")
    op.drop_index("ix_accounts_pairwise_sub", table_name="accounts")
    op.drop_table("accounts")
