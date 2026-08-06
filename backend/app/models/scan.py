"""SENTINEL AI X — Scan / pipeline execution model."""

from __future__ import annotations

from enum import Enum as PyEnum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class ScanStatus(str, PyEnum):
    """Pipeline execution status."""
    QUEUED = "queued"
    INDEXING = "indexing"
    SCANNING = "scanning"
    PATCHING = "patching"
    TESTING = "testing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanTrigger(str, PyEnum):
    """What triggered this scan."""
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    MANUAL = "manual"
    SCHEDULE = "schedule"


class Scan(Base):
    """A single pipeline execution triggered by a GitHub event."""

    __tablename__ = "scans"

    # Relationships
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id"), index=True
    )
    repository: Mapped["Repository"] = relationship(back_populates="scans")  # noqa: F821

    # Git context
    commit_sha: Mapped[str] = mapped_column(String(40), index=True)
    branch: Mapped[str] = mapped_column(String(255))
    trigger: Mapped[ScanTrigger] = mapped_column(
        Enum(ScanTrigger), default=ScanTrigger.PUSH
    )
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Execution
    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus), default=ScanStatus.QUEUED, index=True
    )
    current_agent: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Results summary
    total_findings: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    high_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, default=0)
    low_count: Mapped[int] = mapped_column(Integer, default=0)
    patches_generated: Mapped[int] = mapped_column(Integer, default=0)
    tests_generated: Mapped[int] = mapped_column(Integer, default=0)
    security_score: Mapped[int] = mapped_column(Integer, default=100)
    confidence: Mapped[int] = mapped_column(Integer, default=0)  # 0-100

    # Outputs
    threat_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    pr_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Duration
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Child relationships
    findings: Mapped[list["Finding"]] = relationship(back_populates="scan", lazy="selectin")  # noqa: F821
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="scan", lazy="selectin")  # noqa: F821
    patches: Mapped[list["Patch"]] = relationship(back_populates="scan", lazy="selectin")  # noqa: F821
