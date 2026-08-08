"""
OBSIDIAN — GitHub Event Sourcing Model.

Every GitHub webhook event is persisted for:
  - Audit trail
  - Digital Twin incremental updates
  - Security Time Machine (Feature 5)
  - Event replay and debugging

Events are processed asynchronously by Celery workers.
"""

from __future__ import annotations

from enum import Enum as PyEnum

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class GitHubEventType(str, PyEnum):
    """All supported GitHub webhook event types."""

    PUSH = "push"
    PULL_REQUEST = "pull_request"
    PULL_REQUEST_REVIEW = "pull_request_review"
    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"
    RELEASE = "release"
    CREATE = "create"
    DELETE = "delete"
    BRANCH_PROTECTION_RULE = "branch_protection_rule"
    DEPLOYMENT = "deployment"
    DEPLOYMENT_STATUS = "deployment_status"
    WORKFLOW_RUN = "workflow_run"
    WORKFLOW_JOB = "workflow_job"
    CHECK_RUN = "check_run"
    CHECK_SUITE = "check_suite"
    SECURITY_ADVISORY = "security_advisory"
    SECRET_SCANNING_ALERT = "secret_scanning_alert"
    CODE_SCANNING_ALERT = "code_scanning_alert"
    DEPENDABOT_ALERT = "dependabot_alert"
    REPOSITORY = "repository"
    INSTALLATION = "installation"
    INSTALLATION_REPOSITORIES = "installation_repositories"
    MEMBER = "member"
    DISCUSSION = "discussion"
    DISCUSSION_COMMENT = "discussion_comment"


class ProcessingStatus(str, PyEnum):
    """Event processing lifecycle."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class GitHubEvent(Base):
    """
    A single GitHub webhook event received by OBSIDIAN.

    Events are the atomic unit of change in the Digital Twin.
    Each event triggers an incremental graph update and optionally
    a partial or full security pipeline run.
    """

    __tablename__ = "github_events"

    # ── Event Identity ────────────────────────────────────────
    event_type: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False,
    )
    action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    delivery_id: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True,
    )

    # ── Repository Link ───────────────────────────────────────
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id"), index=True, nullable=False,
    )
    repository: Mapped["Repository"] = relationship()  # noqa: F821

    # ── Sender ────────────────────────────────────────────────
    sender: Mapped[str] = mapped_column(String(255), nullable=False)

    # ── Deduplication ─────────────────────────────────────────
    payload_hash: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False,
    )

    # ── Payload ───────────────────────────────────────────────
    payload: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Git Context (extracted from payload) ──────────────────
    commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Processing ────────────────────────────────────────────
    processing_status: Mapped[str] = mapped_column(
        String(20), default=ProcessingStatus.PENDING.value, index=True,
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Pipeline Link (if scan was triggered) ─────────────────
    scan_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("scans.id"), nullable=True,
    )

    # ── Digital Twin ──────────────────────────────────────────
    twin_nodes_created: Mapped[int] = mapped_column(Integer, default=0)
    twin_nodes_updated: Mapped[int] = mapped_column(Integer, default=0)
    twin_edges_created: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_github_events_repo_type", "repository_id", "event_type"),
        Index("ix_github_events_created", "created_at"),
    )
