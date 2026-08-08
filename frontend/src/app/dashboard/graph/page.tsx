"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Network,
  ZoomIn,
  ZoomOut,
  Maximize,
  RotateCcw,
  Shield,
} from "lucide-react";

// ── Types ────────────────────────────────────────────────

interface GraphNode {
  id: string;
  label: string;
  type: string;
  x: number;
  y: number;
  color: string;
  radius: number;
}

interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
}

// ── Color Map ────────────────────────────────────────────

const nodeColors: Record<string, string> = {
  Repository: "#00f0ff",
  File: "#3b82f6",
  Function: "#8b5cf6",
  Class: "#6366f1",
  Dependency: "#ff6600",
  Vulnerability: "#ff3366",
  Threat: "#ec4899",
  Secret: "#fbbf24",
  Agent: "#00ff88",
  Fix: "#10b981",
  Test: "#a855f7",
  CloudResource: "#06b6d4",
  Container: "#14b8a6",
};

// ── Demo Graph Data ──────────────────────────────────────

function generateDemoGraph(): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodeData = [
    { id: "repo-1", label: "obsidian-org/web-api", type: "Repository" },
    { id: "file-1", label: "auth/login.py", type: "File" },
    { id: "file-2", label: "api/routes.py", type: "File" },
    { id: "file-3", label: "models/user.py", type: "File" },
    { id: "file-4", label: "config/settings.py", type: "File" },
    { id: "file-5", label: "Dockerfile", type: "File" },
    { id: "file-6", label: "terraform/main.tf", type: "File" },
    { id: "dep-1", label: "fastapi==0.109.0", type: "Dependency" },
    { id: "dep-2", label: "sqlalchemy==2.0.25", type: "Dependency" },
    { id: "dep-3", label: "pyjwt==2.8.0", type: "Dependency" },
    { id: "dep-4", label: "boto3==1.34.0", type: "Dependency" },
    { id: "vuln-1", label: "SQL Injection (CWE-89)", type: "Vulnerability" },
    { id: "vuln-2", label: "Hardcoded Secret (CWE-798)", type: "Vulnerability" },
    { id: "vuln-3", label: "Missing AuthZ (CWE-862)", type: "Vulnerability" },
    { id: "threat-1", label: "STRIDE: Elevation", type: "Threat" },
    { id: "threat-2", label: "STRIDE: Info Disclosure", type: "Threat" },
    { id: "agent-1", label: "Code Intelligence", type: "Agent" },
    { id: "agent-2", label: "Secrets Detection", type: "Agent" },
    { id: "agent-3", label: "API Security", type: "Agent" },
    { id: "fix-1", label: "Patch: Parameterized Query", type: "Fix" },
    { id: "fix-2", label: "Patch: Env Variables", type: "Fix" },
  ];

  // Position nodes in a force-directed-like layout
  const cx = 500, cy = 350;
  const nodes: GraphNode[] = nodeData.map((n, i) => {
    const angle = (i / nodeData.length) * Math.PI * 2;
    const typeRadii: Record<string, number> = {
      Repository: 0,
      File: 120,
      Dependency: 200,
      Vulnerability: 250,
      Threat: 280,
      Agent: 310,
      Fix: 330,
    };
    const r = typeRadii[n.type] || 180;
    const jitter = (Math.random() - 0.5) * 60;
    return {
      ...n,
      x: cx + Math.cos(angle) * r + jitter,
      y: cy + Math.sin(angle) * r + jitter,
      color: nodeColors[n.type] || "#6b7280",
      radius: n.type === "Repository" ? 20 : n.type === "Vulnerability" ? 14 : 10,
    };
  });

  const edges: GraphEdge[] = [
    { source: "repo-1", target: "file-1", relationship: "CONTAINS" },
    { source: "repo-1", target: "file-2", relationship: "CONTAINS" },
    { source: "repo-1", target: "file-3", relationship: "CONTAINS" },
    { source: "repo-1", target: "file-4", relationship: "CONTAINS" },
    { source: "repo-1", target: "file-5", relationship: "CONTAINS" },
    { source: "repo-1", target: "file-6", relationship: "CONTAINS" },
    { source: "repo-1", target: "dep-1", relationship: "DEPENDS_ON" },
    { source: "repo-1", target: "dep-2", relationship: "DEPENDS_ON" },
    { source: "repo-1", target: "dep-3", relationship: "DEPENDS_ON" },
    { source: "repo-1", target: "dep-4", relationship: "DEPENDS_ON" },
    { source: "file-1", target: "vuln-1", relationship: "HAS_VULNERABILITY" },
    { source: "file-4", target: "vuln-2", relationship: "HAS_VULNERABILITY" },
    { source: "file-2", target: "vuln-3", relationship: "HAS_VULNERABILITY" },
    { source: "vuln-1", target: "threat-1", relationship: "ENABLES" },
    { source: "vuln-2", target: "threat-2", relationship: "ENABLES" },
    { source: "agent-1", target: "vuln-1", relationship: "DISCOVERED" },
    { source: "agent-2", target: "vuln-2", relationship: "DISCOVERED" },
    { source: "agent-3", target: "vuln-3", relationship: "DISCOVERED" },
    { source: "vuln-1", target: "fix-1", relationship: "FIXED_BY" },
    { source: "vuln-2", target: "fix-2", relationship: "FIXED_BY" },
  ];

  return { nodes, edges };
}

// ── Graph Canvas Component ───────────────────────────────

export default function GraphPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [graphData] = useState(generateDemoGraph);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);
    ctx.save();
    ctx.translate(offset.x, offset.y);
    ctx.scale(zoom, zoom);

    // Draw edges
    graphData.edges.forEach((edge) => {
      const src = graphData.nodes.find((n) => n.id === edge.source);
      const tgt = graphData.nodes.find((n) => n.id === edge.target);
      if (!src || !tgt) return;

      ctx.beginPath();
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
      ctx.strokeStyle =
        edge.relationship === "HAS_VULNERABILITY"
          ? "rgba(255, 51, 102, 0.3)"
          : edge.relationship === "FIXED_BY"
          ? "rgba(0, 255, 136, 0.3)"
          : edge.relationship === "DISCOVERED"
          ? "rgba(0, 240, 255, 0.2)"
          : "rgba(100, 116, 139, 0.15)";
      ctx.lineWidth = edge.relationship === "HAS_VULNERABILITY" ? 2 : 1;
      ctx.stroke();
    });

    // Draw nodes
    graphData.nodes.forEach((node) => {
      // Glow
      const gradient = ctx.createRadialGradient(
        node.x, node.y, 0,
        node.x, node.y, node.radius * 2.5
      );
      gradient.addColorStop(0, node.color + "30");
      gradient.addColorStop(1, "transparent");
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius * 2.5, 0, Math.PI * 2);
      ctx.fill();

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
      ctx.fillStyle = node.color + "20";
      ctx.fill();
      ctx.strokeStyle = node.color;
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Label
      ctx.font = "10px Inter, sans-serif";
      ctx.fillStyle = "#94a3b8";
      ctx.textAlign = "center";
      ctx.fillText(
        node.label.length > 24 ? node.label.slice(0, 22) + "…" : node.label,
        node.x,
        node.y + node.radius + 14
      );
    });

    ctx.restore();
  }, [graphData, zoom, offset]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const resize = () => {
      const parent = canvas.parentElement;
      if (!parent) return;
      canvas.width = parent.clientWidth;
      canvas.height = parent.clientHeight;
      draw();
    };

    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, [draw]);

  useEffect(() => {
    draw();
  }, [draw]);

  // Mouse interaction
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left - offset.x) / zoom;
    const my = (e.clientY - rect.top - offset.y) / zoom;

    const found = graphData.nodes.find(
      (n) => Math.hypot(n.x - mx, n.y - my) < n.radius + 5
    );
    setHoveredNode(found || null);
    canvas.style.cursor = found ? "pointer" : "default";
  };

  // Drag
  const [dragging, setDragging] = useState(false);
  const [lastPos, setLastPos] = useState({ x: 0, y: 0 });

  const handleMouseDown = (e: React.MouseEvent) => {
    setDragging(true);
    setLastPos({ x: e.clientX, y: e.clientY });
  };
  const handleMouseUp = () => setDragging(false);
  const handleDrag = (e: React.MouseEvent) => {
    if (!dragging) return;
    setOffset((prev) => ({
      x: prev.x + (e.clientX - lastPos.x),
      y: prev.y + (e.clientY - lastPos.y),
    }));
    setLastPos({ x: e.clientX, y: e.clientY });
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">Knowledge Graph</h1>
          <p className="text-sm text-gray-500 mt-1">
            Security knowledge graph — files, vulnerabilities, threats, agents,
            and patches
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setZoom((z) => Math.min(z + 0.2, 3))}
            className="p-2 rounded-lg glass-card hover:bg-white/5 transition-colors"
          >
            <ZoomIn className="w-4 h-4 text-gray-400" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(z - 0.2, 0.3))}
            className="p-2 rounded-lg glass-card hover:bg-white/5 transition-colors"
          >
            <ZoomOut className="w-4 h-4 text-gray-400" />
          </button>
          <button
            onClick={() => { setZoom(1); setOffset({ x: 0, y: 0 }); }}
            className="p-2 rounded-lg glass-card hover:bg-white/5 transition-colors"
          >
            <RotateCcw className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="glass-card p-3 flex flex-wrap gap-4">
        {Object.entries(nodeColors)
          .filter(([t]) =>
            ["Repository", "File", "Dependency", "Vulnerability", "Threat", "Agent", "Fix"].includes(t)
          )
          .map(([type, color]) => (
            <div key={type} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{
                  backgroundColor: color,
                  boxShadow: `0 0 6px ${color}50`,
                }}
              />
              <span className="text-xs text-gray-400">{type}</span>
            </div>
          ))}
      </div>

      {/* Canvas */}
      <div className="glass-card relative" style={{ height: "calc(100vh - 280px)" }}>
        <canvas
          ref={canvasRef}
          onMouseMove={handleMouseMove}
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onMouseMoveCapture={handleDrag}
          className="w-full h-full"
        />

        {/* Hover Tooltip */}
        {hoveredNode && (
          <div className="absolute top-4 right-4 glass-card p-4 min-w-[200px] animate-fade-in">
            <div className="flex items-center gap-2 mb-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: hoveredNode.color }}
              />
              <span className="text-xs font-semibold text-gray-300">
                {hoveredNode.type}
              </span>
            </div>
            <p className="text-sm text-gray-200 font-mono">
              {hoveredNode.label}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Connections:{" "}
              {graphData.edges.filter(
                (e) =>
                  e.source === hoveredNode.id || e.target === hoveredNode.id
              ).length}
            </p>
          </div>
        )}

        {/* Scan Line */}
        <div className="scan-line-overlay rounded-xl" />
      </div>
    </motion.div>
  );
}
