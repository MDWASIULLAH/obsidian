"""SENTINEL AI X — Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════
# Enums (mirrored from SQLAlchemy for API layer)
# ═══════════════════════════════════════════════════════════════════

class SeverityEnum(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ScanStatusEnum(str, Enum):
    QUEUED = "queued"
    INDEXING = "indexing"
    SCANNING = "scanning"
    PATCHING = "patching"
    TESTING = "testing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PatchStatusEnum(str, Enum):
    GENERATED = "generated"
    TESTING = "testing"
    VERIFIED = "verified"
    APPLIED = "applied"
    REJECTED = "rejected"
    FAILED = "failed"


# ═══════════════════════════════════════════════════════════════════
# Repository Schemas
# ═══════════════════════════════════════════════════════════════════

class RepositoryCreate(BaseModel):
    full_name: str = Field(..., description="GitHub repo in owner/repo format")
    github_token: str | None = Field(None, description="Optional PAT for private repos")


class RepositoryResponse(BaseModel):
    id: str
    github_id: int
    full_name: str
    name: str
    owner: str
    default_branch: str
    description: str | None
    language: str | None
    is_active: bool
    security_score: int
    total_scans: int
    total_findings: int
    total_patches: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# Scan Schemas
# ═══════════════════════════════════════════════════════════════════

class ScanCreate(BaseModel):
    repository_id: str
    commit_sha: str | None = None
    branch: str | None = None


class ScanResponse(BaseModel):
    id: str
    repository_id: str
    commit_sha: str
    branch: str
    trigger: str
    status: ScanStatusEnum
    current_agent: str | None
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    patches_generated: int
    tests_generated: int
    security_score: int
    confidence: int
    threat_model: str | None
    pr_url: str | None
    error_message: str | None
    duration_seconds: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScanSummary(BaseModel):
    """Compact scan summary for lists."""
    id: str
    commit_sha: str
    branch: str
    status: ScanStatusEnum
    security_score: int
    total_findings: int
    critical_count: int
    high_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# Finding Schemas
# ═══════════════════════════════════════════════════════════════════

class FindingResponse(BaseModel):
    id: str
    scan_id: str
    title: str
    description: str
    severity: SeverityEnum
    category: str
    confidence: float
    file_path: str | None
    line_start: int | None
    line_end: int | None
    code_snippet: str | None
    cwe_id: str | None
    cve_id: str | None
    owasp_category: str | None
    mitre_technique: str | None
    agent_name: str
    reasoning: str | None
    recommendation: str | None
    citations: str | None
    is_fixed: bool
    is_false_positive: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# Agent Schemas
# ═══════════════════════════════════════════════════════════════════

class AgentRunResponse(BaseModel):
    id: str
    scan_id: str
    agent_name: str
    agent_purpose: str
    status: AgentStatusEnum
    model_used: str | None
    model_tier: str | None
    findings_count: int
    confidence_score: float
    output_summary: str | None
    duration_ms: int | None
    tokens_used: int | None
    error_message: str | None
    retry_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentInfo(BaseModel):
    """Static agent description for the registry."""
    name: str
    purpose: str
    model_tier: str
    reasoning_strategy: str
    inputs: list[str]
    outputs: list[str]


# ═══════════════════════════════════════════════════════════════════
# Patch Schemas
# ═══════════════════════════════════════════════════════════════════

class PatchResponse(BaseModel):
    id: str
    scan_id: str
    file_path: str
    finding_id: str | None
    diff: str
    explanation: str
    status: PatchStatusEnum
    tests_passed: bool
    tests_generated: int
    confidence_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# Dashboard Schemas
# ═══════════════════════════════════════════════════════════════════

class DashboardOverview(BaseModel):
    """Main dashboard data."""
    total_repositories: int
    active_scans: int
    total_findings: int
    critical_findings: int
    average_security_score: float
    patches_generated: int
    tests_generated: int
    recent_scans: list[ScanSummary]
    severity_distribution: dict[str, int]
    agent_performance: list[AgentPerformance]


class AgentPerformance(BaseModel):
    """Agent aggregate metrics."""
    agent_name: str
    total_runs: int
    avg_confidence: float
    avg_duration_ms: float
    total_findings: int
    success_rate: float


class SecurityTimeline(BaseModel):
    """Time-series data for risk visualization."""
    date: str
    security_score: int
    findings_count: int
    critical_count: int
    patches_count: int


# ═══════════════════════════════════════════════════════════════════
# Webhook Schemas
# ═══════════════════════════════════════════════════════════════════

class WebhookPayload(BaseModel):
    """Parsed GitHub webhook event."""
    event_type: str
    action: str | None = None
    repository_full_name: str
    sender: str
    commit_sha: str | None = None
    branch: str | None = None
    pr_number: int | None = None
    diff_url: str | None = None


# ═══════════════════════════════════════════════════════════════════
# Knowledge Graph Schemas
# ═══════════════════════════════════════════════════════════════════

class GraphNode(BaseModel):
    """A node in the security knowledge graph."""
    id: str
    label: str
    type: str
    properties: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """An edge in the security knowledge graph."""
    source: str
    target: str
    relationship: str
    properties: dict = Field(default_factory=dict)


class GraphData(BaseModel):
    """Full graph data for visualization."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ═══════════════════════════════════════════════════════════════════
# Generic
# ═══════════════════════════════════════════════════════════════════

class HealthCheck(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    services: dict[str, str] = Field(default_factory=dict)


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    items: list = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


# ═══════════════════════════════════════════════════════════════════
# Digital Twin Schemas
# ═══════════════════════════════════════════════════════════════════

class DigitalTwinNode(BaseModel):
    """A node in the Digital Twin graph."""
    id: str
    label: str
    type: str
    health: float = Field(1.0, ge=0.0, le=1.0, description="Node health 0-1")
    risk: float = Field(0.0, ge=0.0, le=1.0, description="Risk score 0-1")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence 0-1")
    security_score: int = Field(100, ge=0, le=100, description="Security score 0-100")
    owner: str | None = None
    last_modified: str | None = None
    properties: dict = Field(default_factory=dict)


class DigitalTwinEdge(BaseModel):
    """An edge in the Digital Twin graph."""
    source: str
    target: str
    relationship: str
    properties: dict = Field(default_factory=dict)


class DigitalTwinStats(BaseModel):
    """Summary statistics for a Digital Twin."""
    node_counts: dict[str, int] = Field(default_factory=dict)
    edge_counts: dict[str, int] = Field(default_factory=dict)
    total_nodes: int = 0
    total_edges: int = 0
    overall_health: float = 1.0
    overall_risk: float = 0.0
    overall_security_score: int = 100
    last_event_at: str | None = None


class DigitalTwinResponse(BaseModel):
    """Full Digital Twin data for frontend visualization."""
    repository_id: str
    repository_name: str
    nodes: list[DigitalTwinNode]
    edges: list[DigitalTwinEdge]
    stats: DigitalTwinStats


class DigitalTwinNodeDetail(BaseModel):
    """Detailed view of a single node with neighbors."""
    node: DigitalTwinNode
    neighbors: list[DigitalTwinNode]
    edges: list[DigitalTwinEdge]
    recent_events: list[dict] = Field(default_factory=list)


class DigitalTwinSearchResult(BaseModel):
    """Search result within the Digital Twin."""
    nodes: list[DigitalTwinNode]
    total: int


# ═══════════════════════════════════════════════════════════════════
# GitHub Event Schemas
# ═══════════════════════════════════════════════════════════════════

class GitHubEventResponse(BaseModel):
    """API response for a stored GitHub event."""
    id: str
    event_type: str
    action: str | None
    repository_id: str
    sender: str
    commit_sha: str | None
    branch: str | None
    pr_number: int | None
    processing_status: str
    processing_error: str | None
    twin_nodes_created: int
    twin_nodes_updated: int
    twin_edges_created: int
    created_at: datetime

    model_config = {"from_attributes": True}


class EventRouteConfig(BaseModel):
    """Describes which agents activate for each event type."""
    event_type: str
    requires_full_pipeline: bool
    requires_graph_update: bool
    activated_agents: list[str]


# ═══════════════════════════════════════════════════════════════════
# Threat Evolution
# ═══════════════════════════════════════════════════════════════════

class ThreatSnapshotResponse(BaseModel):
    """Single point-in-time threat state."""
    id: str
    severity: str
    score: float | None = None
    confidence: float | None = None
    captured_at: str | None = None
    agent: str | None = None
    file_path: str | None = None
    mitre: str | None = None
    phase: str | None = None


class ThreatTimelineResponse(BaseModel):
    """Full evolution timeline for one threat."""
    threat_id: str
    repo: str
    metadata: dict = {}
    snapshots: list[ThreatSnapshotResponse] = []
    snapshot_count: int = 0
    velocity: float = 0.0
    trend: str = "stable"
    first_seen: str | None = None
    last_seen: str | None = None


class ThreatTimelineSummary(BaseModel):
    """Summary row for the all-timelines listing."""
    threat_id: str
    title: str | None = None
    severity: str | None = None
    category: str | None = None
    cwe: str | None = None
    cve: str | None = None
    mitre: str | None = None
    phase: str | None = None
    snap_count: int = 0
    velocity: float = 0.0
    trend: str = "stable"
    latest_score: float = 0.0
    first_seen: str | None = None
    last_seen: str | None = None


class ThreatTrajectoryResponse(BaseModel):
    """LLM-predicted future trajectory."""
    id: str | None = None
    predictions: list[dict] = []
    model: str | None = None
    confidence: float = 0.0
    created_at: str | None = None


class ExploitabilityRankingResponse(BaseModel):
    """Single threat ranked by exploitability urgency."""
    threat_id: str
    title: str | None = None
    severity: str | None = None
    category: str | None = None
    velocity: float = 0.0
    trend: str = "stable"
    latest_score: float = 0.0
    urgency_score: float = 0.0


# ═══════════════════════════════════════════════════════════════════
# Attack Chain
# ═══════════════════════════════════════════════════════════════════

class AttackChainNode(BaseModel):
    id: str
    label: str
    type: str
    severity: str | None = None
    mitre_phase: str | None = None
    risk: float = 0.0
    security_score: int = 50

class AttackChainEdge(BaseModel):
    type: str
    source: str
    target: str

class AttackChainResponse(BaseModel):
    id: str
    repo_full_name: str
    entry_node: AttackChainNode | None = None
    target_node: AttackChainNode | None = None
    nodes: list[AttackChainNode] = []
    edges: list[AttackChainEdge] = []
    chain_length: int = 0
    severity_score: float = 0.0
    kill_chain_phases: list[str] = []
    discovered_at: str | None = None

class AttackMovieFrame(BaseModel):
    sequence: int
    node: AttackChainNode
    edge: AttackChainEdge | None = None
    action: str
    kill_chain_phase: str = "unknown"
    kill_chain_order: int = 99
    severity_at_hop: str = "medium"
    cumulative_risk: float = 0.0
    delay_ms: int = 1500

class AttackMovieResponse(BaseModel):
    chain_id: str | None = None
    title: str
    total_frames: int
    total_duration_ms: int
    severity_score: float = 0.0
    kill_chain_phases: list[str] = []
    frames: list[AttackMovieFrame] = []

class BlastRadiusNode(BaseModel):
    id: str
    label: str
    type: str
    severity: str | None = None
    risk: float = 0.0
    security_score: int = 50
    distance: int = 0

class BlastRadiusResponse(BaseModel):
    origin_node_id: str
    repo_full_name: str
    total_reachable: int
    nodes: list[BlastRadiusNode] = []
    type_distribution: dict[str, int] = {}
    severity_distribution: dict[str, int] = {}
    max_depth: int = 4


# ═══════════════════════════════════════════════════════════════════
# Business Impact
# ═══════════════════════════════════════════════════════════════════

class BusinessImpactRequest(BaseModel):
    annual_revenue: float = 10_000_000
    industry: str = "default"
    estimated_records: int = 100_000
    compliance_frameworks: list[str] = ["GDPR", "SOC2"]

class ThreatImpactItem(BaseModel):
    threat_id: str
    title: str
    severity: str
    breach_cost: float
    record_exposure_cost: float
    downtime_cost: float
    downtime_hours: int
    asset_criticality: float
    affected_asset_count: int
    total_impact: float

class RegulatoryExposureItem(BaseModel):
    framework: str
    max_fine: float
    estimated_exposure: float
    relevant_threat_count: int
    regions: list[str]

class ImpactSummary(BaseModel):
    total_financial_risk: float
    breach_cost_total: float
    downtime_cost_total: float
    record_exposure_total: float
    regulatory_exposure_total: float
    chain_amplification_factor: float
    threat_count: int
    critical_threats: int
    high_value_assets: int
    attack_chain_count: int

class BusinessImpactResponse(BaseModel):
    repo_full_name: str
    computed_at: str
    summary: ImpactSummary
    industry: str
    annual_revenue: float
    estimated_records: int
    compliance_frameworks: list[str]
    threat_impacts: list[ThreatImpactItem]
    regulatory_exposure: list[RegulatoryExposureItem]
    risk_rating: str


# ═══════════════════════════════════════════════════════════════════
# Security Timeline
# ═══════════════════════════════════════════════════════════════════

class TimelineSnapshotSummary(BaseModel):
    id: str
    captured_at: str | None = None
    trigger: str | None = None
    security_score: int = 50
    total_threats: int = 0
    total_vulnerabilities: int = 0
    total_assets: int = 0
    attack_chain_count: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    risk_score: float = 0.0

class TimelineSnapshotDetail(TimelineSnapshotSummary):
    repo_full_name: str = ""
    event_id: str | None = None
    threat_counts: dict[str, int] = {}
    vulnerability_counts: dict[str, int] = {}
    asset_breakdown: dict[str, int] = {}

class DiffDelta(BaseModel):
    before: float | int
    after: float | int
    delta: float | int

class TimelineDiffResponse(BaseModel):
    snapshot_a: dict[str, str | None]
    snapshot_b: dict[str, str | None]
    security_score: DiffDelta
    risk_score: DiffDelta
    total_threats: DiffDelta
    total_vulnerabilities: DiffDelta
    total_assets: DiffDelta
    attack_chain_count: DiffDelta
    critical_findings: DiffDelta
    threat_severity_diff: dict[str, DiffDelta] = {}
    posture_direction: str = "stable"

class PostureTrendDataPoint(BaseModel):
    captured_at: str | None = None
    security_score: int | None = None
    risk_score: float | None = None
    total_threats: int | None = None
    critical_findings: int | None = None

class PostureTrendResponse(BaseModel):
    repo_full_name: str
    period_days: int
    snapshots_count: int
    trend: str
    score_delta: int = 0
    risk_delta: float = 0.0
    threat_delta: int = 0
    first_snapshot: TimelineSnapshotSummary | None = None
    last_snapshot: TimelineSnapshotSummary | None = None
    data_points: list[PostureTrendDataPoint] = []
