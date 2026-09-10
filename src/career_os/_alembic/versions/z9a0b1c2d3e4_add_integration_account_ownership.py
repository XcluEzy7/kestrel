"""Scope integration configurations to accounts.

Revision ID: z9a0b1c2d3e4
Revises: y7z8a9b0c1d2

Existing integration rows stay unowned (account_id NULL). Operators or an
explicit migration may assign them; this migration never guesses ownership.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "z9a0b1c2d3e4"
down_revision: str | None = "y7z8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("integration_configs") as batch_op:
        batch_op.add_column(sa.Column("account_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_integration_configs_account_id", ["account_id"])
        batch_op.create_foreign_key(
            "fk_integration_configs_account_id_accounts",
            "accounts",
            ["account_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_index(op.f("ix_integration_configs_name"))
        batch_op.create_unique_constraint(
            "uq_integration_configs_account_name", ["account_id", "name"]
        )


def downgrade() -> None:
    with op.batch_alter_table("integration_configs") as batch_op:
        batch_op.drop_constraint("uq_integration_configs_account_name", type_="unique")
        batch_op.create_index(op.f("ix_integration_configs_name"), ["name"], unique=True)
        batch_op.drop_constraint("fk_integration_configs_account_id_accounts", type_="foreignkey")
        batch_op.drop_index("ix_integration_configs_account_id")
        batch_op.drop_column("account_id")
