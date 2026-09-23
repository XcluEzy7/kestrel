"""Allow provider model to remain empty until model discovery."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "z9a0b1c2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("provider_connections") as batch_op:
        batch_op.alter_column("model", nullable=True)


def downgrade() -> None:
    null_count = op.get_bind().execute(
        sa.text("SELECT COUNT(*) FROM provider_connections WHERE model IS NULL")
    ).scalar_one()
    if null_count:
        raise RuntimeError(
            "Cannot downgrade provider_connections.model to NOT NULL: "
            f"found {null_count} row(s) with NULL model. "
            "Assign a real model to each affected provider connection before retrying."
        )

    with op.batch_alter_table("provider_connections") as batch_op:
        batch_op.alter_column("model", nullable=False)
