"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Cpu, RefreshCw, Search, Filter, ZoomIn, ZoomOut, Maximize2,
  X, ChevronRight, AlertTriangle, Shield, Activity, GitBranch,
  Clock, Radio
} from "lucide-react";
import { api, createDigitalTwinWebSocket } from "@/lib/api";
import type {
  DigitalTwinData, DigitalTwinNode, DigitalTwinEdge,
  TwinNodeDetail, GitHubEventItem, Repository
} from "@/lib/api";

// ─── Node type colour palette ─────────────────────────────────────
const NODE_COLORS: Record<string, string> = {
  Repository: "#6366f1", Branch: "#8b5cf6", Commit: "#a78bfa",
  File: "#06b6d4", Function: "#0891b2", Class: "#0e7490",
  Module: "#155e75", Dependency: "#f59e0b", Container: "#10b981",
  DockerImage: "#059669", TerraformResource: "#6d28d9",
  GitHubAction: "#7c3aed", Secret: "#ef4444", CloudResource: "#f97316",
  APIEndpoint: "#ec4899", TrustBoundary: "#64748b", AuthFlow: "#dc2626",
  DataFlow: "#2563eb", DatabaseConnection: "#7c3aed",
  ExternalService: "#d97706", Infrastructure: "#374151",
  Vulnerability: "#dc2626", Threat: "#b91c1c",
};

const getRiskColor = (risk: number) =>
  risk > 0.7 ? "#ef4444" : risk > 0.4 ? "#f59e0b" : "#10b981";

// ─── Stats Bar ────────────────────────────────────────────────────
function StatsBar({ data, liveCount }: { data: DigitalTwinData; liveCount: number }) {
  const s = data.stats;
  return (
    <div className="flex items-center gap-6 px-6 py-3 border-b border-white/5 bg-surface-950/60 text-sm flex-wrap">
      <div className="flex items-center gap-2 text-cyber-cyan font-semibold">
        <Cpu className="w-4 h-4" />
        <span>{data.repository_name}</span>
      </div>
      <Stat label="Nodes" value={s.total_nodes} />
      <Stat label="Edges" value={s.total_edges} />
      <Stat label="Security" value={`${s.overall_security_score}/100`} />
      <Stat label="Health" value={`${Math.round(s.overall_health * 100)}%`} />
      {liveCount > 0 && (
        <div className="ml-auto flex items-center gap-1.5 text-emerald-400">
          <Radio className="w-3.5 h-3.5 animate-pulse" />
          <span className="text-xs">Live · {liveCount} updates</span>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-gray-500 text-xs">{label}:</span>
      <span className="text-white font-medium">{value}</span>
    </div>
  );
}

// ─── Node Detail Panel ────────────────────────────────────────────
function NodeDetailPanel({
  detail, onClose
}: { detail: TwinNodeDetail; onClose: () => void }) {
  const { node, neighbors, edges } = detail;
  const color = NODE_COLORS[node.type] ?? "#6b7280";
  return (
    <motion.div
      initial={{ x: 320, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 320, opacity: 0 }}
      transition={{ type: "spring", damping: 20 }}
      className="w-80 flex-shrink-0 border-l border-white/5 bg-surface-950/90 backdrop-blur-xl overflow-y-auto"
    >
      <div className="p-4 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ background: color }} />
          <span className="font-semibold text-sm truncate max-w-[180px]">{node.label}</span>
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Type badge */}
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded-full text-xs font-medium"
            style={{ background: `${color}22`, color }}>
            {node.type}
          </span>
        </div>

        {/* Scores */}
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: "Security", value: node.security_score, max: 100, unit: "" },
            { label: "Health", value: Math.round(node.health * 100), max: 100, unit: "%" },
            { label: "Risk", value: Math.round(node.risk * 100), max: 100, unit: "%" },
          ].map(({ label, value, unit }) => (
            <div key={label} className="bg-white/5 rounded-lg p-2 text-center">
              <div className="text-lg font-bold" style={{ color: label === "Risk" ? getRiskColor(node.risk) : "#06b6d4" }}>
                {value}{unit}
              </div>
              <div className="text-[10px] text-gray-500 uppercase tracking-wide">{label}</div>
            </div>
          ))}
        </div>

        {/* Properties */}
        {Object.keys(node.properties).length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Properties</h4>
            <div className="space-y-1">
              {Object.entries(node.properties).slice(0, 8).map(([k, v]) => (
                <div key={k} className="flex justify-between text-xs">
                  <span className="text-gray-500 truncate max-w-[100px]">{k}</span>
                  <span className="text-gray-300 truncate max-w-[140px] text-right">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Connected edges */}
        {edges.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
              Relationships ({edges.length})
            </h4>
            <div className="space-y-1">
              {edges.slice(0, 6).map((e, i) => (
                <div key={i} className="flex items-center gap-1.5 text-xs text-gray-400">
                  <ChevronRight className="w-3 h-3 text-cyber-cyan flex-shrink-0" />
                  <span className="font-mono text-[10px] text-purple-400">{e.relationship}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Neighbors */}
        {neighbors.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
              Neighbors ({neighbors.length})
            </h4>
            <div className="space-y-1">
              {neighbors.slice(0, 8).map((nb) => (
                <div key={nb.id} className="flex items-center gap-2 text-xs py-1">
                  <div className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ background: NODE_COLORS[nb.type] ?? "#6b7280" }} />
                  <span className="text-gray-300 truncate">{nb.label}</span>
                  <span className="ml-auto text-[10px] text-gray-600">{nb.type}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ─── Event Feed ───────────────────────────────────────────────────
function EventFeed({ events }: { events: GitHubEventItem[] }) {
  const EVENT_ICONS: Record<string, string> = {
    push: "🔀", pull_request: "🔄", deployment: "🚀",
    security_advisory: "⚠️", dependabot_alert: "📦",
    secret_scanning_alert: "🔑", code_scanning_alert: "🔍",
    workflow_run: "⚙️", create: "✨", delete: "🗑️",
  };
  return (
    <div className="h-full overflow-y-auto">
      <div className="p-3 border-b border-white/5">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5" /> Event Feed
        </h3>
      </div>
      <div className="divide-y divide-white/5">
        {events.length === 0 && (
          <div className="p-4 text-center text-gray-600 text-sm">No events yet</div>
        )}
        {events.map((e) => (
          <div key={e.id} className="p-3 hover:bg-white/5 transition-colors">
            <div className="flex items-start gap-2">
              <span className="text-sm">{EVENT_ICONS[e.event_type] ?? "📡"}</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-medium text-white capitalize">{e.event_type.replace("_", " ")}</span>
                  {e.action && (
                    <span className="text-[10px] text-gray-500">· {e.action}</span>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-0.5 text-[10px] text-gray-500">
                  <span>{e.sender}</span>
                  {e.branch && <span>on {e.branch}</span>}
                </div>
                {(e.twin_nodes_created + e.twin_nodes_updated) > 0 && (
                  <div className="text-[10px] text-emerald-500 mt-0.5">
                    +{e.twin_nodes_created} nodes · ~{e.twin_nodes_updated} updated
                  </div>
                )}
              </div>
              <div className="flex items-center gap-1 text-[10px] text-gray-600 flex-shrink-0">
                <Clock className="w-2.5 h-2.5" />
                {new Date(e.created_at).toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Cytoscape Graph Canvas ────────────────────────────────────────
function CytoscapeGraph({
  nodes, edges, onNodeClick, searchQuery, filterType
}: {
  nodes: DigitalTwinNode[];
  edges: DigitalTwinEdge[];
  onNodeClick: (node: DigitalTwinNode) => void;
  searchQuery: string;
  filterType: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);

  const filteredNodes = nodes.filter((n) => {
    if (filterType && n.type !== filterType) return false;
    if (searchQuery && !n.label.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });
  const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));
  const filteredEdges = edges.filter(
    (e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
  );

  useEffect(() => {
    if (!containerRef.current || filteredNodes.length === 0) return;

    // Dynamically import cytoscape to avoid SSR issues
    import("cytoscape").then((cytoscapeModule) => {
      const cytoscape = cytoscapeModule.default;

      if (cyRef.current) {
        cyRef.current.destroy();
      }

      const cy = cytoscape({
        container: containerRef.current,
        elements: [
          ...filteredNodes.map((n) => ({
            data: {
              id: n.id,
              label: n.label.length > 20 ? n.label.slice(0, 18) + "…" : n.label,
              type: n.type,
              color: NODE_COLORS[n.type] ?? "#6b7280",
              risk: n.risk,
              security_score: n.security_score,
              _original: n,
            },
          })),
          ...filteredEdges.map((e, i) => ({
            data: {
              id: `e-${i}`,
              source: e.source,
              target: e.target,
              label: e.relationship,
            },
          })),
        ],
        style: [
          {
            selector: "node",
            style: {
              "background-color": "data(color)",
              "label": "data(label)",
              "color": "#e2e8f0",
              "font-size": "10px",
              "text-valign": "bottom",
              "text-margin-y": "4px",
              "width": (ele: any) => Math.max(20, 40 - ele.data("risk") * 20),
              "height": (ele: any) => Math.max(20, 40 - ele.data("risk") * 20),
              "border-width": (ele: any) => ele.data("risk") > 0.7 ? 2 : 0,
              "border-color": "#ef4444",
              "overlay-padding": "4px",
            } as any,
          },
          {
            selector: "node:selected",
            style: {
              "border-width": 3,
              "border-color": "#06b6d4",
              "overlay-opacity": 0.1,
            } as any,
          },
          {
            selector: "edge",
            style: {
              "width": 1,
              "line-color": "#374151",
              "target-arrow-color": "#374151",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              "label": "data(label)",
              "font-size": "8px",
              "color": "#4b5563",
              "text-rotation": "autorotate",
            } as any,
          },
        ],
        layout: { name: "cose", animate: false, randomize: false },
        userZoomingEnabled: true,
        userPanningEnabled: true,
        boxSelectionEnabled: false,
      });

      cy.on("tap", "node", (evt: any) => {
        const n = evt.target.data("_original") as DigitalTwinNode;
        if (n) onNodeClick(n);
      });

      cyRef.current = cy;
    });

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [filteredNodes.length, filteredEdges.length, searchQuery, filterType]);

  const zoom = (dir: number) => cyRef.current?.zoom(cyRef.current.zoom() + dir * 0.2);
  const fit = () => cyRef.current?.fit(undefined, 40);

  return (
    <div className="relative flex-1">
      <div ref={containerRef} className="w-full h-full" />
      {/* Zoom controls */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-1">
        {[
          { icon: ZoomIn, action: () => zoom(1) },
          { icon: ZoomOut, action: () => zoom(-1) },
          { icon: Maximize2, action: fit },
        ].map(({ icon: Icon, action }, i) => (
          <button key={i} onClick={action}
            className="w-8 h-8 bg-surface-900/80 border border-white/10 rounded-lg flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-colors backdrop-blur-sm">
            <Icon className="w-4 h-4" />
          </button>
        ))}
      </div>
      {filteredNodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center text-gray-600">
            <Cpu className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">No nodes match current filters</p>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────
export default function DigitalTwinPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>("");
  const [twinData, setTwinData] = useState<DigitalTwinData | null>(null);
  const [selectedNodeDetail, setSelectedNodeDetail] = useState<TwinNodeDetail | null>(null);
  const [events, setEvents] = useState<GitHubEventItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState("");
  const [liveUpdateCount, setLiveUpdateCount] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);

  // Load repos
  useEffect(() => {
    api.listRepositories().then((r) => {
      setRepos(r);
      if (r.length > 0) setSelectedRepo(r[0].id);
    });
  }, []);

  // Load twin data + events when repo changes
  useEffect(() => {
    if (!selectedRepo) return;
    setLoading(true);
    setSelectedNodeDetail(null);
    Promise.all([
      api.getDigitalTwin(selectedRepo),
      api.listRepoEvents(selectedRepo, 1, 50),
    ]).then(([twin, evts]) => {
      setTwinData(twin);
      setEvents(evts.items);
    }).finally(() => setLoading(false));
  }, [selectedRepo]);

  // WebSocket for live updates
  useEffect(() => {
    if (!selectedRepo) return;
    wsRef.current?.close();
    wsRef.current = createDigitalTwinWebSocket(
      selectedRepo,
      (msg) => {
        if (msg.type === "twin_update") {
          setLiveUpdateCount((c) => c + 1);
          // Refresh data silently
          api.getDigitalTwin(selectedRepo).then(setTwinData);
          api.listRepoEvents(selectedRepo, 1, 50).then((r) => setEvents(r.items));
        }
      }
    );
    return () => wsRef.current?.close();
  }, [selectedRepo]);

  const handleNodeClick = useCallback(async (node: DigitalTwinNode) => {
    const detail = await api.getDigitalTwinNode(selectedRepo, node.id);
    setSelectedNodeDetail(detail);
  }, [selectedRepo]);

  const nodeTypes = twinData
    ? [...new Set(twinData.nodes.map((n) => n.type))].sort()
    : [];

  return (
    <div className="flex flex-col h-full bg-surface-950">
      {/* ── Header ── */}
      <div className="flex items-center gap-4 px-6 py-4 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-cyber-cyan/10 rounded-lg border border-cyber-cyan/20">
            <Cpu className="w-5 h-5 text-cyber-cyan" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">AI Security Digital Twin</h1>
            <p className="text-xs text-gray-500">Live repository graph · Updated on every GitHub event</p>
          </div>
        </div>

        <div className="ml-auto flex items-center gap-3">
          {/* Repo selector */}
          <select
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
            className="bg-surface-900 border border-white/10 text-sm text-white rounded-lg px-3 py-2 focus:outline-none focus:border-cyber-cyan/50"
          >
            {repos.map((r) => (
              <option key={r.id} value={r.id}>{r.full_name}</option>
            ))}
          </select>

          <button
            onClick={() => selectedRepo && api.getDigitalTwin(selectedRepo).then(setTwinData)}
            disabled={loading}
            className="p-2 border border-white/10 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* ── Stats bar ── */}
      {twinData && <StatsBar data={twinData} liveCount={liveUpdateCount} />}

      {/* ── Main layout ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Event feed */}
        <div className="w-56 flex-shrink-0 border-r border-white/5 bg-surface-950/80 overflow-hidden flex flex-col">
          <EventFeed events={events} />
        </div>

        {/* Centre: Graph + filter toolbar */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Filter toolbar */}
          <div className="flex items-center gap-3 px-4 py-2.5 border-b border-white/5 bg-surface-950/60">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
              <input
                type="text"
                placeholder="Search nodes…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg pl-8 pr-3 py-1.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-cyber-cyan/50"
              />
            </div>

            <div className="flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-gray-500" />
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-cyber-cyan/50"
              >
                <option value="">All types</option>
                {nodeTypes.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            {twinData && (
              <div className="ml-auto flex items-center gap-4 text-xs text-gray-500">
                {Object.entries(twinData.stats.node_counts).slice(0, 4).map(([type, count]) => (
                  <div key={type} className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full"
                      style={{ background: NODE_COLORS[type] ?? "#6b7280" }} />
                    <span>{type}: {count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Graph canvas */}
          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="w-12 h-12 border-2 border-cyber-cyan/30 border-t-cyber-cyan rounded-full animate-spin mx-auto mb-4" />
                <p className="text-sm text-gray-500">Loading Digital Twin…</p>
              </div>
            </div>
          ) : twinData ? (
            <CytoscapeGraph
              nodes={twinData.nodes}
              edges={twinData.edges}
              onNodeClick={handleNodeClick}
              searchQuery={searchQuery}
              filterType={filterType}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center text-gray-600">
                <Cpu className="w-16 h-16 mx-auto mb-4 opacity-20" />
                <p className="text-sm">Select a repository to view its Digital Twin</p>
                <p className="text-xs mt-1">The graph updates automatically on every GitHub event</p>
              </div>
            </div>
          )}
        </div>

        {/* Right: Node detail panel */}
        <AnimatePresence>
          {selectedNodeDetail && (
            <NodeDetailPanel
              detail={selectedNodeDetail}
              onClose={() => setSelectedNodeDetail(null)}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
