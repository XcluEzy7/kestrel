"""Allow provider model to remain empty until model discovery."""

from collections.abc import Sequence

from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "z9a0b1c2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("provider_connections") as batch_op:
        batch_op.alter_column("model", nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("provider_connections") as batch_op:
        batch_op.alter_column("model", nullable=False)
