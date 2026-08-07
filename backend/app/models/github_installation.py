"""GitHub App installation records."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class GitHubInstallation(Base):
    """A GitHub App installation for a user or organization account."""

    __tablename__ = "github_installations"

    installation_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    account_login: Mapped[str] = mapped_column(String(255), index=True)
    account_type: Mapped[str] = mapped_column(String(50), default="User")
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    repository_selection: Mapped[str] = mapped_column(String(50), default="selected")
    permissions: Mapped[dict] = mapped_column(JSON, default=dict)
    events: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    user: Mapped["User | None"] = relationship()  # noqa: F821
