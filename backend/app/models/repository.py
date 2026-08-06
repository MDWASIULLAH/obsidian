"""SENTINEL AI X — Repository model."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class Repository(Base):
    """A GitHub repository tracked by Sentinel."""

    __tablename__ = "repositories"

    # GitHub metadata
    github_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # owner/repo
    name: Mapped[str] = mapped_column(String(255))
    owner: Mapped[str] = mapped_column(String(255))
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    clone_url: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Sentinel tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    security_score: Mapped[int] = mapped_column(Integer, default=100)  # 0-100
    total_scans: Mapped[int] = mapped_column(Integer, default=0)
    total_findings: Mapped[int] = mapped_column(Integer, default=0)
    total_patches: Mapped[int] = mapped_column(Integer, default=0)

    # Installation
    installation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    scans: Mapped[list["Scan"]] = relationship(back_populates="repository", lazy="selectin")  # noqa: F821
