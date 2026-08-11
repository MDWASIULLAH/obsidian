"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { RotateCcw, ZoomIn, ZoomOut, Activity, RefreshCw } from "lucide-react";

type ApiNode = {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
};

type ApiEdge = {
  source: string;
  target: string;
  relationship: string;
};

type LiveGraph = {
  repository_id: string;
  repository_name: string;
  nodes: ApiNode[];
  edges: ApiEdge[];
  meta: {
    generated_at: string;
    active_scans: number;
    finding_count: number;
  };
};

type RenderNode = ApiNode & { x: number; y: number; vx: number; vy: number };

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const NODE_COLORS: Record<string, string> = {
  Repository: "#00f0ff",
  Scan: "#8b5cf6",
  File: "#3b82f6",
  Vulnerability: "#ff3366",
  Agent: "#00ff88",
};

const FALLBACK_COLOR = "#94a3b8";

function colorFor(type: string) {
  return NODE_COLORS[type] || FALLBACK_COLOR;
}

function makeInitialPositions(nodes: ApiNode[], width: number, height: number): RenderNode[] {
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.max(80, Math.min(width, height) * 0.28);

  return nodes.map((node, index) => {
    const angle = (index / Math.max(nodes.length, 1)) * Math.PI * 2;
    const r = node.type === "Repository" ? 0 : radius + (index % 3) * 35;
    return {
      ...node,
      x: cx + Math.cos(angle) * r,
      y: cy + Math.sin(angle) * r,
      vx: 0,
      vy: 0,
    };
  });
}

export default function GraphPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dataRef = useRef<LiveGraph | null>(null);
  const nodesRef = useRef<RenderNode[]>([]);
  const frameRef = useRef<number | null>(null);
  const transformRef = useRef({ zoom: 1, x: 0, y: 0 });
  const dragRef = useRef({ active: false, x: 0, y: 0 });

  const [repositories, setRepositories] = useState<Array<{ id: string; full_name: string }>>([]);
  const [repoId, setRepoId] = useState<string>("");
  const [data, setData] = useState<LiveGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [hovered, setHovered] = useState<RenderNode | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadRepositories = useCallback(async () => {
    const response = await fetch(`${API_BASE}/api/v1/repositories`, { cache: "no-store" });
    if (!response.ok) throw new Error(`Repository API returned ${response.status}`);
    const items = await response.json();
    const normalized = items.map((item: any) => ({ id: item.id, full_name: item.full_name }));
    setRepositories(normalized);
    if (!repoId && normalized[0]?.id) setRepoId(normalized[0].id);
  }, [repoId]);

  const loadGraph = useCallback(async () => {
    if (!repoId) return;
    try {
      const response = await fetch(`${API_BASE}/api/v1/live-graph/${repoId}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`Live graph API returned ${response.status}`);
      const next: LiveGraph = await response.json();
      dataRef.current = next;
      setData(next);
      setLastUpdated(new Date());
      setError("");

      const canvas = canvasRef.current;
      if (canvas) {
        const previous = new Map(nodesRef.current.map((node) => [node.id, node]));
        nodesRef.current = next.nodes.map((node) => {
          const old = previous.get(node.id);
          return old
            ? { ...node, x: old.x, y: old.y, vx: old.vx, vy: old.vy }
            : makeInitialPositions([node], canvas.width, canvas.height)[0];
        });
      }
    } catch (err: any) {
      setError(err?.message || "Unable to load live graph");
    } finally {
      setLoading(false);
    }
  }, [repoId]);

  useEffect(() => {
    loadRepositories().catch((err) => {
      setLoading(false);
      setError(err?.message || "Unable to load repositories");
    });
  }, [loadRepositories]);

  useEffect(() => {
    if (!repoId) return;
    loadGraph();
    const timer = window.setInterval(loadGraph, data?.meta.active_scans ? 1500 : 3000);
    return () => window.clearInterval(timer);
  }, [repoId, loadGraph, data?.meta.active_scans]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const graph = dataRef.current;
    if (!canvas || !graph) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const nodes = nodesRef.current;
    const nodeMap = new Map(nodes.map((node) => [node.id, node]));

    // Lightweight force simulation driven only by the real graph nodes/edges.
    for (const node of nodes) {
      let fx = 0;
      let fy = 0;
      for (const other of nodes) {
        if (other.id === node.id) continue;
        const dx = node.x - other.x;
        const dy = node.y - other.y;
        const d2 = Math.max(dx * dx + dy * dy, 100);
        if (d2 < 180000) {
          const force = 1800 / d2;
          fx += dx * force;
          fy += dy * force;
        }
      }

      for (const edge of graph.edges) {
        if (edge.source !== node.id && edge.target !== node.id) continue;
        const otherId = edge.source === node.id ? edge.target : edge.source;
        const other = nodeMap.get(otherId);
        if (!other) continue;
        const dx = other.x - node.x;
        const dy = other.y - node.y;
        fx += dx * 0.0018;
        fy += dy * 0.0018;
      }

      if (node.type === "Repository") {
        fx += (width / 2 - node.x) * 0.012;
        fy += (height / 2 - node.y) * 0.012;
      } else {
        fx += (width / 2 - node.x) * 0.0008;
        fy += (height / 2 - node.y) * 0.0008;
      }

      node.vx = (node.vx + fx) * 0.92;
      node.vy = (node.vy + fy) * 0.92;
      node.x += node.vx;
      node.y += node.vy;
      node.x = Math.max(35, Math.min(width - 35, node.x));
      node.y = Math.max(35, Math.min(height - 35, node.y));
    }

    const { zoom, x: ox, y: oy } = transformRef.current;
    ctx.clearRect(0, 0, width, height);
    ctx.save();
    ctx.translate(ox, oy);
    ctx.scale(zoom, zoom);

    // Connections from the real API response.
    for (const edge of graph.edges) {
      const source = nodeMap.get(edge.source);
      const target = nodeMap.get(edge.target);
      if (!source || !target) continue;
      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);
      ctx.strokeStyle = edge.relationship === "HAS_VULNERABILITY"
        ? "rgba(255,51,102,.48)"
        : "rgba(100,116,139,.22)";
      ctx.lineWidth = edge.relationship === "HAS_VULNERABILITY" ? 2 : 1;
      ctx.stroke();
    }

    const pulse = 1 + Math.sin(performance.now() / 500) * 0.08;
    for (const node of nodes) {
      const color = colorFor(node.type);
      const radius = node.type === "Repository" ? 13 : node.type === "Vulnerability" ? 10 : 7;

      const glow = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, radius * 3.5 * pulse);
      glow.addColorStop(0, `${color}44`);
      glow.addColorStop(1, "transparent");
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius * 3.5 * pulse, 0, Math.PI * 2);
      ctx.fill();

      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = `${color}20`;
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = node.type === "Vulnerability" ? 2 : 1.5;
      ctx.stroke();

      ctx.font = "11px Inter, sans-serif";
      ctx.fillStyle = "#cbd5e1";
      ctx.textAlign = "center";
      const label = node.label.length > 30 ? `${node.label.slice(0, 28)}…` : node.label;
      ctx.fillText(label, node.x, node.y + radius + 15);
    }

    ctx.restore();
    frameRef.current = requestAnimationFrame(draw);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const parent = canvas.parentElement;
    if (!parent) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const rect = parent.getBoundingClientRect();
      canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      ctxScale(canvas, dpr);
    };

    resize();
    window.addEventListener("resize", resize);
    frameRef.current = requestAnimationFrame(draw);
    return () => {
      window.removeEventListener("resize", resize);
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [draw]);

  function ctxScale(canvas: HTMLCanvasElement, dpr: number) {
    const ctx = canvas.getContext("2d");
    if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  const pointerNode = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const { zoom, x, y } = transformRef.current;
    const mx = (event.clientX - rect.left - x) / zoom;
    const my = (event.clientY - rect.top - y) / zoom;
    const found = nodesRef.current.find((node) => Math.hypot(node.x - mx, node.y - my) < 18);
    setHovered(found || null);
  };

  const zoomBy = (amount: number) => {
    transformRef.current.zoom = Math.max(0.35, Math.min(3, transformRef.current.zoom + amount));
  };

  const reset = () => {
    transformRef.current = { zoom: 1, x: 0, y: 0 };
    const canvas = canvasRef.current;
    if (canvas && dataRef.current) {
      nodesRef.current = makeInitialPositions(dataRef.current.nodes, canvas.clientWidth, canvas.clientHeight);
    }
  };

  const active = Boolean(data?.meta.active_scans);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-gray-100">Knowledge Graph</h1>
            <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-semibold ${active ? "bg-cyan-400/10 text-cyan-300" : "bg-emerald-400/10 text-emerald-300"}`}>
              <Activity className="w-3 h-3" />
              {active ? "LIVE SCAN" : "LIVE DATA"}
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-1">Real repository scans, findings, files and agents. No demo nodes.</p>
        </div>
        <div className="flex items-center gap-2">
          {repositories.length > 0 && (
            <select value={repoId} onChange={(e) => setRepoId(e.target.value)} className="bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-xs text-gray-300 max-w-[240px]">
              {repositories.map((repo) => <option key={repo.id} value={repo.id}>{repo.full_name}</option>)}
            </select>
          )}
          <button onClick={loadGraph} className="p-2 rounded-lg glass-card hover:bg-white/5" title="Refresh live graph"><RefreshCw className="w-4 h-4 text-gray-400" /></button>
          <button onClick={() => zoomBy(0.2)} className="p-2 rounded-lg glass-card hover:bg-white/5"><ZoomIn className="w-4 h-4 text-gray-400" /></button>
          <button onClick={() => zoomBy(-0.2)} className="p-2 rounded-lg glass-card hover:bg-white/5"><ZoomOut className="w-4 h-4 text-gray-400" /></button>
          <button onClick={reset} className="p-2 rounded-lg glass-card hover:bg-white/5"><RotateCcw className="w-4 h-4 text-gray-400" /></button>
        </div>
      </div>

      <div className="glass-card p-3 flex flex-wrap gap-4">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
            <span className="text-xs text-gray-400">{type}</span>
          </div>
        ))}
        <span className="text-xs text-gray-600 ml-auto">{data?.nodes.length || 0} nodes · {data?.edges.length || 0} edges · {data?.meta.finding_count || 0} findings</span>
      </div>

      <div className="glass-card relative overflow-hidden" style={{ height: "calc(100vh - 300px)", minHeight: 480 }}>
        {loading && <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/30"><div className="text-sm text-gray-500">Loading real graph data…</div></div>}
        {error && <div className="absolute inset-x-4 top-4 z-20 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-xs text-red-300">{error}</div>}
        {!loading && !error && !data?.nodes.length && <div className="absolute inset-0 flex items-center justify-center text-sm text-gray-500">Run a real repository scan to populate the graph.</div>}
        <canvas
          ref={canvasRef}
          className="w-full h-full touch-none"
          onPointerMove={pointerNode}
          onPointerLeave={() => setHovered(null)}
          onPointerDown={(e) => { dragRef.current = { active: true, x: e.clientX, y: e.clientY }; }}
          onPointerUp={() => { dragRef.current.active = false; }}
          onPointerCancel={() => { dragRef.current.active = false; }}
        />
        {hovered && (
          <div className="absolute right-4 top-4 glass-card p-4 min-w-[220px] pointer-events-none">
            <div className="flex items-center gap-2 mb-2"><span className="w-2.5 h-2.5 rounded-full" style={{ background: colorFor(hovered.type) }} /><span className="text-[10px] uppercase text-gray-500">{hovered.type}</span></div>
            <p className="text-sm text-gray-100 font-mono break-words">{hovered.label}</p>
            {hovered.properties?.severity && <p className="text-xs text-red-300 mt-2">Severity: {String(hovered.properties.severity)}</p>}
            {hovered.properties?.file_path && <p className="text-xs text-gray-500 mt-1 break-all">{String(hovered.properties.file_path)}</p>}
          </div>
        )}
        <div className="absolute bottom-3 left-3 text-[10px] text-gray-600">Updated {lastUpdated ? lastUpdated.toLocaleTimeString() : "—"} · refreshes automatically</div>
      </div>
    </motion.div>
  );
}
