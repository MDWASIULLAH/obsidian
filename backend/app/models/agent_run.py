"""OBSIDIAN — Agent execution run model."""

from __future__ import annotations

from enum import Enum as PyEnum

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class AgentStatus(str, PyEnum):
    """Agent run status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentRun(Base):
    """An individual agent execution within a pipeline scan."""

    __tablename__ = "agent_runs"

    # Parent scan
    scan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scans.id"), index=True
    )
    scan: Mapped["Scan"] = relationship(back_populates="agent_runs")  # noqa: F821

    # Agent identity
    agent_name: Mapped[str] = mapped_column(String(100), index=True)
    agent_purpose: Mapped[str] = mapped_column(String(500))

    # Execution
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus), default=AgentStatus.PENDING
    )
    model_used: Mapped[str | None] = mapped_column(String(200), nullable=True)
    model_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Results
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    reasoning_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Performance
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
