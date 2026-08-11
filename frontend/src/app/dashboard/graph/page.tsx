"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Activity, Maximize2, RefreshCw, RotateCcw, ZoomIn, ZoomOut } from "lucide-react";

type Node = { id: string; label: string; type: string; properties: Record<string, unknown> };
type Edge = { source: string; target: string; relationship: string };
type Graph = { repository_id: string; repository_name: string; nodes: Node[]; edges: Edge[]; meta: { generated_at: string; active_scans: number; finding_count: number; scan_count: number } };
type VNode = Node & { x: number; y: number; z: number; phase: number };

const API = (process.env.NEXT_PUBLIC_API_URL || "https://obsidian-backend-gute.onrender.com").replace(/\/$/, "");
const COLORS: Record<string, string> = { Repository: "#00e5ff", File: "#3b82f6", Dependency: "#ff7900", Vulnerability: "#ff3366", Threat: "#ec4899", Agent: "#00ff88", Fix: "#10b981", Scan: "#8b5cf6" };
function color(type: string) { return COLORS[type] || "#94a3b8"; }
function hash(value: string) { let h = 0; for (let i = 0; i < value.length; i++) h = ((h << 5) - h + value.charCodeAt(i)) | 0; return Math.abs(h); }

function project(n: VNode, width: number, height: number, time: number, zoom: number) {
  const ry = time * 0.00018, rx = Math.sin(time * 0.00011) * 0.22;
  const cy = Math.cos(ry), sy = Math.sin(ry), x1 = n.x * cy - n.z * sy, z1 = n.x * sy + n.z * cy;
  const cx = Math.cos(rx), sx = Math.sin(rx), y1 = n.y * cx - z1 * sx, z2 = n.y * sx + z1 * cx;
  const depth = 1 / Math.max(0.55, 1 + z2 / 900);
  return { x: width / 2 + x1 * depth * zoom, y: height / 2 + y1 * depth * zoom, scale: depth, z: z2 };
}

function initialNodes(nodes: Node[], width: number, height: number): VNode[] {
  const radius = Math.min(width, height) * 0.32;
  return nodes.map((n, i) => {
    if (n.type === "Repository") return { ...n, x: 0, y: 0, z: 0, phase: 0 };
    const h = hash(n.id), theta = (i / Math.max(nodes.length, 1)) * Math.PI * 2 + (h % 100) / 100;
    const phi = ((h % 180) * Math.PI) / 180, r = radius * (0.55 + ((h % 100) / 100) * 0.8);
    return { ...n, x: Math.cos(theta) * r, y: Math.sin(theta) * Math.cos(phi) * r, z: Math.sin(phi) * r, phase: (h % 628) / 100 };
  });
}

export default function GraphPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null), graphRef = useRef<Graph | null>(null), nodesRef = useRef<VNode[]>([]);
  const frameRef = useRef<number | undefined>(undefined), zoomRef = useRef(1);
  const [repos, setRepos] = useState<Array<{ id: string; full_name: string }>>([]), [repoId, setRepoId] = useState("");
  const [graph, setGraph] = useState<Graph | null>(null), [error, setError] = useState(""), [loading, setLoading] = useState(true);
  const [hovered, setHovered] = useState<VNode | null>(null), [fullscreen, setFullscreen] = useState(false);

  const loadGraph = useCallback(async () => {
    if (!repoId) return;
    try {
      const res = await fetch(`${API}/api/v1/live-graph/${repoId}?t=${Date.now()}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`Graph API returned ${res.status}`);
      const next: Graph = await res.json(); graphRef.current = next; setGraph(next); setError("");
      const canvas = canvasRef.current;
      if (canvas) {
        const old = new Map(nodesRef.current.map(n => [n.id, n]));
        const fresh = initialNodes(next.nodes, canvas.clientWidth || 800, canvas.clientHeight || 600);
        nodesRef.current = fresh.map(n => old.has(n.id) ? { ...n, x: old.get(n.id)!.x, y: old.get(n.id)!.y, z: old.get(n.id)!.z, phase: old.get(n.id)!.phase } : n);
      }
    } catch (e: any) { setError(e?.message || "Unable to load live graph"); } finally { setLoading(false); }
  }, [repoId]);

  useEffect(() => {
    fetch(`${API}/api/v1/repositories`, { cache: "no-store" }).then(r => { if (!r.ok) throw new Error(`Repository API returned ${r.status}`); return r.json(); }).then(items => {
      const list = (Array.isArray(items) ? items : []).map((x: any) => ({ id: x.id, full_name: x.full_name }));
      setRepos(list); if (!repoId && list[0]) setRepoId(list[0].id);
    }).catch(e => { setLoading(false); setError(e?.message || "Unable to load repositories"); });
  }, [repoId]);

  useEffect(() => {
    if (!repoId) return; loadGraph();
    const interval = window.setInterval(loadGraph, graph?.meta.active_scans ? 1000 : 2500);
    return () => window.clearInterval(interval);
  }, [repoId, loadGraph, graph?.meta.active_scans]);

  const draw = useCallback((time: number) => {
    const canvas = canvasRef.current, g = graphRef.current;
    if (!canvas || !g) { frameRef.current = requestAnimationFrame(draw); return; }
    const ctx = canvas.getContext("2d"); if (!ctx) return;
    const rect = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1, width = rect.width, height = rect.height;
    if (canvas.width !== Math.floor(width * dpr) || canvas.height !== Math.floor(height * dpr)) { canvas.width = Math.max(1, Math.floor(width * dpr)); canvas.height = Math.max(1, Math.floor(height * dpr)); }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, width, height);
    const nodes = nodesRef.current, positions = new Map(nodes.map(n => [n.id, project(n, width, height, time, zoomRef.current)]));
    ctx.fillStyle = "#08090c"; ctx.fillRect(0, 0, width, height);
    const grad = ctx.createRadialGradient(width / 2, height / 2, 10, width / 2, height / 2, Math.max(width, height) * .65); grad.addColorStop(0, "rgba(20,35,45,.32)"); grad.addColorStop(1, "rgba(0,0,0,0)"); ctx.fillStyle = grad; ctx.fillRect(0, 0, width, height);

    for (const e of g.edges) {
      const a = positions.get(e.source), b = positions.get(e.target); if (!a || !b) continue;
      const hot = e.relationship === "HAS_VULNERABILITY" || e.relationship === "MAPS_TO_THREAT";
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.strokeStyle = hot ? `rgba(255,51,102,${0.28 + a.scale * .18})` : `rgba(65,170,190,${0.12 + a.scale * .12})`; ctx.lineWidth = hot ? 1.7 : 1; ctx.stroke();
      const p = ((time * 0.00008 + hash(e.source + e.target) / 10000) % 1), px = a.x + (b.x - a.x) * p, py = a.y + (b.y - a.y) * p; ctx.fillStyle = hot ? "#ff3366" : "#45dbe8"; ctx.globalAlpha = .7; ctx.beginPath(); ctx.arc(px, py, hot ? 2 : 1.4, 0, Math.PI * 2); ctx.fill(); ctx.globalAlpha = 1;
    }

    [...nodes].sort((a, b) => (positions.get(a.id)?.z || 0) - (positions.get(b.id)?.z || 0)).forEach(n => {
      const p = positions.get(n.id)!; const pulse = 1 + Math.sin(time * 0.004 + n.phase) * 0.12, base = n.type === "Repository" ? 15 : n.type === "Vulnerability" ? 9 : 7, r = Math.max(3, base * p.scale * pulse), c = color(n.type);
      ctx.shadowBlur = 20 * p.scale; ctx.shadowColor = c; const glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r * 3.5); glow.addColorStop(0, `${c}88`); glow.addColorStop(1, `${c}00`); ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(p.x, p.y, r * 3.5, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0;
      ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2); ctx.fillStyle = `${c}22`; ctx.fill(); ctx.strokeStyle = c; ctx.lineWidth = n.type === "Repository" ? 2.5 : 1.5; ctx.stroke();
      if (n.type === "Repository") { ctx.beginPath(); ctx.arc(p.x, p.y, r * .48, 0, Math.PI * 2); ctx.fillStyle = c; ctx.fill(); }
      ctx.font = `${Math.max(9, Math.round(11 * p.scale))}px Inter, sans-serif`; ctx.fillStyle = "#d5dde5"; ctx.textAlign = "center"; ctx.fillText(n.label.length > 28 ? `${n.label.slice(0, 26)}…` : n.label, p.x, p.y + r + 14);
    });
    frameRef.current = requestAnimationFrame(draw);
  }, []);

  useEffect(() => { frameRef.current = requestAnimationFrame(draw); return () => { if (frameRef.current !== undefined) cancelAnimationFrame(frameRef.current); }; }, [draw]);

  const onPointer = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current; if (!canvas) return; const rect = canvas.getBoundingClientRect(); let best: VNode | null = null, distance = 28;
    for (const n of nodesRef.current) { const p = project(n, rect.width, rect.height, performance.now(), zoomRef.current), d = Math.hypot(p.x - (e.clientX - rect.left), p.y - (e.clientY - rect.top)); if (d < distance) { best = n; distance = d; } }
    setHovered(best);
  };

  const reset = () => { zoomRef.current = 1; const canvas = canvasRef.current; if (canvas && graphRef.current) nodesRef.current = initialNodes(graphRef.current.nodes, canvas.clientWidth, canvas.clientHeight); };
  const zoom = (v: number) => { zoomRef.current = Math.max(.45, Math.min(2.4, zoomRef.current + v)); };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3"><div><div className="flex items-center gap-3"><h1 className="text-xl font-bold text-gray-100">Knowledge Graph</h1><span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-cyan-400/10 text-cyan-300 text-[10px] font-semibold"><Activity className="w-3 h-3 animate-pulse" /> LIVE</span></div><p className="text-sm text-gray-500 mt-1">3D repository intelligence — real dependencies, files, vulnerabilities, threats, agents and fixes.</p></div><div className="flex items-center gap-2">{repos.length > 0 && <select value={repoId} onChange={e => setRepoId(e.target.value)} className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs text-gray-300 max-w-[230px]">{repos.map(r => <option key={r.id} value={r.id}>{r.full_name}</option>)}</select>}<button onClick={loadGraph} className="p-2 rounded-lg glass-card"><RefreshCw className="w-4 h-4 text-gray-400" /></button><button onClick={() => zoom(.2)} className="p-2 rounded-lg glass-card"><ZoomIn className="w-4 h-4 text-gray-400" /></button><button onClick={() => zoom(-.2)} className="p-2 rounded-lg glass-card"><ZoomOut className="w-4 h-4 text-gray-400" /></button><button onClick={reset} className="p-2 rounded-lg glass-card"><RotateCcw className="w-4 h-4 text-gray-400" /></button><button onClick={() => setFullscreen(v => !v)} className="p-2 rounded-lg glass-card"><Maximize2 className="w-4 h-4 text-gray-400" /></button></div></div>
      <div className="glass-card p-3 flex flex-wrap gap-x-5 gap-y-2">{Object.entries(COLORS).map(([type, c]) => <div key={type} className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full" style={{ background: c, boxShadow: `0 0 10px ${c}` }} /><span className="text-[11px] text-gray-400">{type}</span></div>)}<span className="text-[11px] text-gray-600 ml-auto">{graph?.nodes.length || 0} nodes · {graph?.edges.length || 0} relationships · {graph?.meta.finding_count || 0} findings</span></div>
      <div className={fullscreen ? "fixed inset-0 z-50 bg-[#08090c] p-4" : "glass-card relative overflow-hidden"} style={fullscreen ? undefined : { height: "calc(100vh - 300px)", minHeight: 520 }}>
        <canvas ref={canvasRef} className="w-full h-full block" onPointerMove={onPointer} onPointerLeave={() => setHovered(null)} />
        {loading && <div className="absolute inset-0 flex items-center justify-center bg-black/30 pointer-events-none"><span className="text-sm text-gray-500">Loading repository intelligence…</span></div>}
        {error && <div className="absolute top-4 left-4 right-4 rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-xs text-red-300">{error}</div>}
        {graph && !graph.nodes.length && !loading && <div className="absolute inset-0 flex items-center justify-center text-sm text-gray-500 pointer-events-none">Run a real scan to build the repository graph.</div>}
        {hovered && <div className="absolute right-4 top-4 w-[250px] glass-card p-4 pointer-events-none"><div className="flex items-center gap-2 mb-2"><span className="w-2.5 h-2.5 rounded-full" style={{ background: color(hovered.type), boxShadow: `0 0 8px ${color(hovered.type)}` }} /><span className="text-[10px] uppercase text-gray-500">{hovered.type}</span></div><div className="text-sm text-gray-100 break-words">{hovered.label}</div>{hovered.properties?.severity != null && <div className="text-xs text-red-300 mt-2">Severity: {String(hovered.properties.severity)}</div>}{hovered.properties?.file_path != null && <div className="text-[11px] text-gray-500 mt-1 break-all">{String(hovered.properties.file_path)}</div>}{hovered.properties?.recommendation != null && <div className="text-[11px] text-emerald-300 mt-2">Fix: {String(hovered.properties.recommendation)}</div>}</div>}
        <div className="absolute bottom-3 left-3 text-[10px] text-gray-600">Real data · graph rotates in 3D · relationships animate · API refreshes automatically</div>
      </div>
    </motion.div>
  );
}
