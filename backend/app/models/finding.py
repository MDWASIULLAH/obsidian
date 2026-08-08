"""OBSIDIAN — Security finding model."""

from __future__ import annotations

from enum import Enum as PyEnum

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class Severity(str, PyEnum):
    """Finding severity level."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, PyEnum):
    """Category of the security finding."""
    VULNERABILITY = "vulnerability"
    SECRET = "secret"
    MISCONFIGURATION = "misconfiguration"
    DEPENDENCY = "dependency"
    LICENSE = "license"
    COMPLIANCE = "compliance"
    DESIGN_FLAW = "design_flaw"
    LOGIC_ERROR = "logic_error"
    PROMPT_INJECTION = "prompt_injection"
    SUPPLY_CHAIN = "supply_chain"


class Finding(Base):
    """An individual security finding produced by an agent."""

    __tablename__ = "findings"

    # Parent scan
    scan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scans.id"), index=True
    )
    scan: Mapped["Scan"] = relationship(back_populates="findings")  # noqa: F821

    # Classification
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), index=True)
    category: Mapped[FindingCategory] = mapped_column(Enum(FindingCategory))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # Location
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Security standards mapping
    cwe_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cve_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    owasp_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mitre_technique: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Agent metadata
    agent_name: Mapped[str] = mapped_column(String(100))
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # RAG citations
    citations: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    # Status
    is_fixed: Mapped[bool] = mapped_column(default=False)
    is_false_positive: Mapped[bool] = mapped_column(default=False)
