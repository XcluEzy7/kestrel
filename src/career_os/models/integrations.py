"""SQLAlchemy ORM model for integration configurations."""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from career_os.database import Base


def _utcnow() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(UTC)


class IntegrationConfig(Base):
    """Configuration for an external integration (TickTick, Calendar, etc.).

    Each row represents one integration's configuration for the system.
    Credentials are stored as a JSON blob in `credentials`.
    """

    __tablename__ = "integration_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    credentials: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON blob
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="not_configured"
    )  # not_configured | connected | error | disabled
    status_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    account: Mapped["Account | None"] = relationship("Account")  # noqa: F821

    def __repr__(self) -> str:
        return f"<IntegrationConfig(name='{self.name}', enabled={self.enabled})>"
