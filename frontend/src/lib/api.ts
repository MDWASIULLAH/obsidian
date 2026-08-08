/**
 * OBSIDIAN — API Client
 *
 * Typed API client for all backend endpoints.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const isBrowser = typeof window !== "undefined";

// ── Types ─────────────────────────────────────────────────

export interface Repository {
  id: string;
  github_id: number;
  full_name: string;
  name: string;
  owner: string;
  default_branch: string;
  description: string | null;
  language: string | null;
  is_active: boolean;
  security_score: number;
  total_scans: number;
  total_findings: number;
  total_patches: number;
  created_at: string;
  updated_at: string;
}

export interface Scan {
  id: string;
  repository_id: string;
  commit_sha: string;
  branch: string;
  trigger: string;
  status: string;
  current_agent: string | null;
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  patches_generated: number;
  tests_generated: number;
  security_score: number;
  confidence: number;
  threat_model: string | null;
  pr_url: string | null;
  duration_seconds: number | null;
  created_at: string;
}

export interface Finding {
  id: string;
  scan_id: string;
  title: string;
  description: string;
  severity: string;
  category: string;
  confidence: number;
  file_path: string | null;
  line_start: number | null;
  line_end: number | null;
  code_snippet: string | null;
  cwe_id: string | null;
  cve_id: string | null;
  owasp_category: string | null;
  mitre_technique: string | null;
  agent_name: string;
  reasoning: string | null;
  recommendation: string | null;
  citations: string | null;
  is_fixed: boolean;
  is_false_positive: boolean;
  created_at: string;
}

export interface AgentInfo {
  name: string;
  purpose: string;
  model_tier: string;
  reasoning_strategy: string;
  inputs: string[];
  outputs: string[];
  metrics: {
    total_runs: number;
    success_rate: number;
    total_findings: number;
  };
}

export interface DashboardData {
  total_repositories: number;
  active_scans: number;
  total_findings: number;
  critical_findings: number;
  average_security_score: number;
  patches_generated: number;
  tests_generated: number;
  recent_scans: Scan[];
  severity_distribution: Record<string, number>;
}

export interface GraphData {
  nodes: { id: string; label: string; type: string; properties: Record<string, any> }[];
  edges: { source: string; target: string; relationship: string }[];
}

export interface Report {
  id: string;
  name: string;
  repository: string;
  date: string;
  score: number;
  findings: number;
  patches: number;
  status: "approved" | "blocked" | "pending";
}

// ── Digital Twin Types ────────────────────────────────────────────

export interface DigitalTwinNode {
  id: string;
  label: string;
  type: string;
  health: number;         // 0-1
  risk: number;           // 0-1
  confidence: number;     // 0-1
  security_score: number; // 0-100
  owner: string | null;
  last_modified: string | null;
  properties: Record<string, string>;
  color?: string;
  icon?: string;
}

export interface DigitalTwinEdge {
  source: string;
  target: string;
  relationship: string;
  properties: Record<string, string>;
}

export interface DigitalTwinStats {
  node_counts: Record<string, number>;
  edge_counts: Record<string, number>;
  total_nodes: number;
  total_edges: number;
  overall_health: number;
  overall_risk: number;
  overall_security_score: number;
  last_event_at: string | null;
}

export interface DigitalTwinData {
  repository_id: string;
  repository_name: string;
  nodes: DigitalTwinNode[];
  edges: DigitalTwinEdge[];
  stats: DigitalTwinStats;
}

export interface TwinNodeDetail {
  node: DigitalTwinNode;
  neighbors: DigitalTwinNode[];
  edges: DigitalTwinEdge[];
  recent_events: Record<string, unknown>[];
}

export interface GitHubEventItem {
  id: string;
  event_type: string;
  action: string | null;
  repository_id: string;
  sender: string;
  commit_sha: string | null;
  branch: string | null;
  pr_number: number | null;
  processing_status: string;
  twin_nodes_created: number;
  twin_nodes_updated: number;
  twin_edges_created: number;
  created_at: string;
}

export interface PaginatedEvents {
  items: GitHubEventItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Threat Evolution Types ─────────────────────────────────────────

export interface ThreatSnapshot {
  id: string;
  severity: string;
  score: number | null;
  confidence: number | null;
  captured_at: string | null;
  agent: string | null;
  file_path: string | null;
  mitre: string | null;
  phase: string | null;
}

export interface ThreatTimeline {
  threat_id: string;
  repo: string;
  metadata: Record<string, unknown>;
  snapshots: ThreatSnapshot[];
  snapshot_count: number;
  velocity: number;
  trend: "escalating" | "stable" | "improving" | "dormant";
  first_seen: string | null;
  last_seen: string | null;
}

export interface ThreatTimelineSummary {
  threat_id: string;
  title: string | null;
  severity: string | null;
  category: string | null;
  cwe: string | null;
  cve: string | null;
  mitre: string | null;
  phase: string | null;
  snap_count: number;
  velocity: number;
  trend: string;
  latest_score: number;
  first_seen: string | null;
  last_seen: string | null;
}

export interface ThreatTrajectory {
  id: string | null;
  predictions: Record<string, unknown>[];
  model: string | null;
  confidence: number;
  created_at: string | null;
}

export interface ExploitabilityRanking {
  threat_id: string;
  title: string | null;
  severity: string | null;
  category: string | null;
  velocity: number;
  trend: string;
  latest_score: number;
  urgency_score: number;
}

// ── Attack Chain Types ───────────────────────────────────────────

export interface AttackChainNode {
  id: string;
  label: string;
  type: string;
  severity: string | null;
  mitre_phase: string | null;
  risk: number;
  security_score: number;
}

export interface AttackChainEdge {
  type: string;
  source: string;
  target: string;
}

export interface AttackChain {
  id: string;
  repo_full_name: string;
  entry_node: AttackChainNode | null;
  target_node: AttackChainNode | null;
  nodes: AttackChainNode[];
  edges: AttackChainEdge[];
  chain_length: number;
  severity_score: number;
  kill_chain_phases: string[];
  discovered_at: string | null;
}

export interface AttackMovieFrame {
  sequence: number;
  node: AttackChainNode;
  edge: AttackChainEdge | null;
  action: string;
  kill_chain_phase: string;
  kill_chain_order: number;
  severity_at_hop: string;
  cumulative_risk: number;
  delay_ms: number;
}

export interface AttackMovie {
  chain_id: string | null;
  title: string;
  total_frames: number;
  total_duration_ms: number;
  severity_score: number;
  kill_chain_phases: string[];
  frames: AttackMovieFrame[];
}

export interface BlastRadiusNode {
  id: string;
  label: string;
  type: string;
  severity: string | null;
  risk: number;
  security_score: number;
  distance: number;
}

export interface BlastRadius {
  origin_node_id: string;
  repo_full_name: string;
  total_reachable: number;
  nodes: BlastRadiusNode[];
  type_distribution: Record<string, number>;
  severity_distribution: Record<string, number>;
  max_depth: number;
}

// ── Business Impact Types ─────────────────────────────────────────

export interface BusinessImpactRequest {
  annual_revenue?: number;
  industry?: string;
  estimated_records?: number;
  compliance_frameworks?: string[];
}

export interface ThreatImpactItem {
  threat_id: string;
  title: string;
  severity: string;
  breach_cost: number;
  record_exposure_cost: number;
  downtime_cost: number;
  downtime_hours: number;
  asset_criticality: number;
  affected_asset_count: number;
  total_impact: number;
}

export interface RegulatoryExposureItem {
  framework: string;
  max_fine: number;
  estimated_exposure: number;
  relevant_threat_count: number;
  regions: string[];
}

export interface ImpactSummary {
  total_financial_risk: number;
  breach_cost_total: number;
  downtime_cost_total: number;
  record_exposure_total: number;
  regulatory_exposure_total: number;
  chain_amplification_factor: number;
  threat_count: number;
  critical_threats: number;
  high_value_assets: number;
  attack_chain_count: number;
}

export interface BusinessImpactData {
  repo_full_name: string;
  computed_at: string;
  summary: ImpactSummary;
  industry: string;
  annual_revenue: number;
  estimated_records: number;
  compliance_frameworks: string[];
  threat_impacts: ThreatImpactItem[];
  regulatory_exposure: RegulatoryExposureItem[];
  risk_rating: string;
}

// ── Security Timeline Types ───────────────────────────────────────

export interface TimelineSnapshotSummary {
  id: string;
  captured_at: string;
  trigger: string;
  security_score: number;
  total_threats: number;
  total_vulnerabilities: number;
  total_assets: number;
  attack_chain_count: number;
  critical_findings: number;
  high_findings: number;
  risk_score: number;
}

export interface TimelineSnapshotDetail extends TimelineSnapshotSummary {
  repo_full_name: string;
  event_id?: string;
  threat_counts: Record<string, number>;
  vulnerability_counts: Record<string, number>;
  asset_breakdown: Record<string, number>;
}

export interface DiffDelta {
  before: number;
  after: number;
  delta: number;
}

export interface TimelineDiffResponse {
  snapshot_a: { id: string; captured_at: string };
  snapshot_b: { id: string; captured_at: string };
  security_score: DiffDelta;
  risk_score: DiffDelta;
  total_threats: DiffDelta;
  total_vulnerabilities: DiffDelta;
  total_assets: DiffDelta;
  attack_chain_count: DiffDelta;
  critical_findings: DiffDelta;
  threat_severity_diff: Record<string, DiffDelta>;
  posture_direction: string;
}

export interface PostureTrendDataPoint {
  captured_at: string;
  security_score: number;
  risk_score: number;
  total_threats: number;
  critical_findings: number;
}

export interface PostureTrendResponse {
  repo_full_name: string;
  period_days: number;
  snapshots_count: number;
  trend: string;
  score_delta: number;
  risk_delta: number;
  threat_delta: number;
  first_snapshot?: TimelineSnapshotSummary;
  last_snapshot?: TimelineSnapshotSummary;
  data_points: PostureTrendDataPoint[];
}


// Fetch Wrapper

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}/api/v1${endpoint}`;
  try {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error ${response.status}`);
    }

    return await response.json();
  } catch (error: any) {
    throw new Error(
      `Backend request failed for ${options.method || "GET"} ${endpoint}: ${error.message || error}`,
    );
  }
}

// ── API Export ─────────────────────────────────────────

export const api = {
  // Dashboard
  getDashboard: () => fetchAPI<DashboardData>("/dashboard"),

  // Repositories
  listRepositories: () => fetchAPI<Repository[]>("/repositories"),
  addRepository: (full_name: string) =>
    fetchAPI<Repository>("/repositories", {
      method: "POST",
      body: JSON.stringify({ full_name }),
    }),
  getRepository: (id: string) => fetchAPI<Repository>(`/repositories/${id}`),

  // Scans
  listScans: (params?: { repository_id?: string; status?: string; page?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.repository_id) searchParams.set("repository_id", params.repository_id);
    if (params?.status) searchParams.set("status", params.status);
    if (params?.page) searchParams.set("page", String(params.page));
    return fetchAPI<{ items: Scan[]; total: number; page: number; total_pages: number }>(
      `/scans?${searchParams}`
    );
  },
  getScan: (id: string) => fetchAPI<Scan>(`/scans/${id}`),
  triggerScan: (repository_id: string) =>
    fetchAPI<Scan>("/scans", {
      method: "POST",
      body: JSON.stringify({ repository_id }),
    }),

  // Findings
  getFindings: (scanId: string, severity?: string) => {
    const params = severity ? `?severity=${severity}` : "";
    return fetchAPI<Finding[]>(`/scans/${scanId}/findings${params}`);
  },
  listFindings: (params?: { severity?: string; page?: number; page_size?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.severity) searchParams.set("severity", params.severity);
    if (params?.page) searchParams.set("page", String(params.page));
    if (params?.page_size) searchParams.set("page_size", String(params.page_size));
    return fetchAPI<{ items: Finding[]; total: number; page: number; total_pages: number }>(
      `/findings?${searchParams.toString()}`,
    );
  },

  // Agents
  listAgents: () => fetchAPI<AgentInfo[]>("/agents"),

  // Knowledge Graph
  getGraph: (repoId: string) => fetchAPI<GraphData>(`/graph/${repoId}`),

  // Knowledge Search
  searchKnowledge: (query: string) =>
    fetchAPI<any[]>(`/knowledge/search?query=${encodeURIComponent(query)}`),
  getKnowledgeStats: () => fetchAPI<Record<string, any>>("/knowledge/stats"),

  // Reports
  listReports: () => fetchAPI<Report[]>("/reports"),
  generateReport: () => fetchAPI<Report>("/reports", { method: "POST" }),

  // ── Digital Twin ─────────────────────────────────────────────────

  getDigitalTwin: (repoId: string) =>
    fetchAPI<DigitalTwinData>(`/digital-twin/${repoId}`),

  getDigitalTwinNode: (repoId: string, nodeId: string) =>
    fetchAPI<TwinNodeDetail>(`/digital-twin/${repoId}/node/${encodeURIComponent(nodeId)}`),

  getDigitalTwinStats: (repoId: string) =>
    fetchAPI<DigitalTwinStats>(`/digital-twin/${repoId}/stats`),

  searchDigitalTwin: (repoId: string, query: string, limit = 50) =>
    fetchAPI<{ nodes: DigitalTwinNode[]; total: number }>(
      `/digital-twin/${repoId}/search?q=${encodeURIComponent(query)}&limit=${limit}`
    ),

  // ── GitHub Events ─────────────────────────────────────────────────

  listEvents: (page = 1, pageSize = 20) =>
    fetchAPI<PaginatedEvents>(`/events?page=${page}&page_size=${pageSize}`),

  listRepoEvents: (repoId: string, page = 1, pageSize = 20, eventType?: string) => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (eventType) params.set("event_type", eventType);
    return fetchAPI<PaginatedEvents>(`/events/${repoId}?${params.toString()}`);
  },

  // ── Threat Evolution ───────────────────────────────────────────

  listThreatTimelines: (repoFullName: string) =>
    fetchAPI<ThreatTimelineSummary[]>(
      `/threat-evolution/${encodeURIComponent(repoFullName)}/timelines`
    ),

  getThreatTimeline: (repoFullName: string, threatId: string) =>
    fetchAPI<ThreatTimeline>(
      `/threat-evolution/${encodeURIComponent(repoFullName)}/timeline/${encodeURIComponent(threatId)}`
    ),

  getThreatPrediction: (threatId: string) =>
    fetchAPI<ThreatTrajectory>(
      `/threat-evolution/prediction/${encodeURIComponent(threatId)}`
    ),

  getExploitabilityRankings: (repoFullName: string, topN = 20) =>
    fetchAPI<ExploitabilityRanking[]>(
      `/threat-evolution/${encodeURIComponent(repoFullName)}/exploitability?top_n=${topN}`
    ),

  // ── Attack Chains ─────────────────────────────────────────────

  discoverAttackChains: (repoFullName: string, maxDepth = 6, limit = 20) =>
    fetchAPI<AttackChain[]>(
      `/attack-chains/${encodeURIComponent(repoFullName)}/discover?max_depth=${maxDepth}&limit=${limit}`
    ),

  listAttackChains: (repoFullName: string, limit = 50) =>
    fetchAPI<AttackChain[]>(
      `/attack-chains/${encodeURIComponent(repoFullName)}/list?limit=${limit}`
    ),

  getAttackMovie: (chain: AttackChain) =>
    fetchAPI<AttackMovie>("/attack-chains/movie", {
      method: "POST",
      body: JSON.stringify(chain),
    }),

  getBlastRadius: (repoFullName: string, nodeId: string, maxDepth = 4) =>
    fetchAPI<BlastRadius>(
      `/attack-chains/${encodeURIComponent(repoFullName)}/blast-radius/${encodeURIComponent(nodeId)}?max_depth=${maxDepth}`
    ),

  // ── Business Impact ───────────────────────────────────────────

  computeBusinessImpact: (repoFullName: string, params?: BusinessImpactRequest) =>
    fetchAPI<BusinessImpactData>(
      `/business-impact/${encodeURIComponent(repoFullName)}`,
      {
        method: "POST",
        body: JSON.stringify(params ?? {}),
      }
    ),

  // ── Security Timeline ─────────────────────────────────────────

  captureSecuritySnapshot: (repoFullName: string, trigger = "manual") =>
    fetchAPI<TimelineSnapshotDetail>(
      `/security-timeline/${encodeURIComponent(repoFullName)}/snapshot?trigger=${trigger}`,
      { method: "POST" }
    ),

  getSecurityTimeline: (repoFullName: string, limit = 50, since?: string) => {
    let url = `/security-timeline/${encodeURIComponent(repoFullName)}/snapshots?limit=${limit}`;
    if (since) url += `&since=${encodeURIComponent(since)}`;
    return fetchAPI<TimelineSnapshotSummary[]>(url);
  },

  diffSecuritySnapshots: (snapshotA: string, snapshotB: string) =>
    fetchAPI<TimelineDiffResponse>(
      `/security-timeline/diff/${encodeURIComponent(snapshotA)}/${encodeURIComponent(snapshotB)}`
    ),

  getPostureTrend: (repoFullName: string, days = 30) =>
    fetchAPI<PostureTrendResponse>(
      `/security-timeline/${encodeURIComponent(repoFullName)}/trend?days=${days}`
    ),
};

// ── Digital Twin WebSocket ──────────────────────────────────────────

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL ||
  (typeof window !== "undefined"
    ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`
    : "ws://localhost:8000");

/**
 * Open a WebSocket connection to receive live Digital Twin updates
 * for a given repository.
 *
 * @returns The WebSocket instance. Call `.close()` to disconnect.
 */
export function createDigitalTwinWebSocket(
  repoId: string,
  onMessage: (data: Record<string, unknown>) => void,
  onError?: (event: Event) => void,
): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/api/v1/ws/digital-twin/${repoId}`);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data as string);
      onMessage(data);
    } catch {
      // non-JSON heartbeat etc.
    }
  };

  ws.onerror = onError ?? ((e) => console.error("Digital Twin WS error", e));

  // Auto ping every 20 s to keep connection alive
  const ping = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "ping" }));
    } else {
      clearInterval(ping);
    }
  }, 20_000);

  ws.onclose = () => clearInterval(ping);

  return ws;
}
