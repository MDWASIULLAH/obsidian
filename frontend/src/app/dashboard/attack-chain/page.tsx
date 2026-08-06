"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Swords, Play, Pause, SkipForward, RefreshCw, AlertTriangle,
  Shield, Target, ChevronRight, X, Crosshair,
} from "lucide-react";
import { api } from "@/lib/api";
import type { AttackChain, AttackMovie, AttackMovieFrame, Repository } from "@/lib/api";

const SEV = { critical: "#ef4444", high: "#f97316", medium: "#f59e0b", low: "#06b6d4", info: "#6b7280" };
const PHASE_COLOR: Record<string, string> = {
  initial_access: "#ef4444", execution: "#f97316", persistence: "#f59e0b",
  privilege_escalation: "#eab308", credential_access: "#a855f7",
  lateral_movement: "#6366f1", exfiltration: "#ec4899", impact: "#dc2626",
  discovery: "#06b6d4", defense_evasion: "#10b981", unknown: "#6b7280",
};

function KillChainBar({ phases, current }: { phases: string[]; current: string }) {
  const all = ["initial_access","execution","persistence","privilege_escalation",
    "defense_evasion","credential_access","discovery","lateral_movement",
    "collection","exfiltration","impact"];
  return (
    <div className="flex gap-0.5">
      {all.map((p) => (
        <div key={p} className="flex-1 h-2 rounded-sm transition-all duration-500"
          style={{
            background: phases.includes(p)
              ? (p === current ? PHASE_COLOR[p] ?? "#6b7280" : `${PHASE_COLOR[p] ?? "#6b7280"}66`)
              : "rgba(255,255,255,0.05)",
          }}
          title={p.replace("_", " ")} />
      ))}
    </div>
  );
}

function MoviePlayer({ movie, onClose }: { movie: AttackMovie; onClose: () => void }) {
  const [frameIdx, setFrameIdx] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const frame = frameIdx >= 0 && frameIdx < movie.frames.length ? movie.frames[frameIdx] : null;

  const stop = () => { if (timerRef.current) clearTimeout(timerRef.current); setPlaying(false); };

  const playNext = useCallback((idx: number) => {
    if (idx >= movie.frames.length) { stop(); return; }
    setFrameIdx(idx);
    timerRef.current = setTimeout(() => playNext(idx + 1), movie.frames[idx]?.delay_ms ?? 1500);
  }, [movie]);

  const togglePlay = () => {
    if (playing) { stop(); return; }
    setPlaying(true);
    playNext(frameIdx < 0 ? 0 : Math.min(frameIdx + 1, movie.frames.length - 1));
  };

  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      className="border border-white/10 rounded-xl bg-surface-900/80 backdrop-blur-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-3 border-b border-white/5">
        <Crosshair className="w-4 h-4 text-red-400" />
        <h3 className="text-sm font-semibold text-white flex-1 truncate">{movie.title}</h3>
        <span className="text-xs text-gray-500">{movie.total_frames} hops · {(movie.total_duration_ms / 1000).toFixed(1)}s</span>
        <button onClick={onClose} className="text-gray-500 hover:text-white"><X className="w-4 h-4" /></button>
      </div>

      {/* Kill chain bar */}
      <div className="px-5 py-2 border-b border-white/5">
        <KillChainBar phases={movie.kill_chain_phases} current={frame?.kill_chain_phase ?? ""} />
        <div className="flex justify-between mt-1 text-[9px] text-gray-600">
          <span>Initial Access</span><span>Impact</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3 px-5 py-2 border-b border-white/5">
        <button onClick={togglePlay}
          className="p-1.5 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 hover:bg-red-500/30 transition-colors">
          {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
        </button>
        <button onClick={() => { stop(); setFrameIdx(Math.min((frameIdx < 0 ? 0 : frameIdx) + 1, movie.frames.length - 1)); }}
          className="p-1.5 border border-white/10 rounded-lg text-gray-400 hover:text-white transition-colors">
          <SkipForward className="w-4 h-4" />
        </button>
        {/* Progress */}
        <div className="flex-1 bg-white/5 rounded-full h-1.5 overflow-hidden">
          <motion.div className="h-full bg-red-500 rounded-full"
            animate={{ width: `${frameIdx < 0 ? 0 : ((frameIdx + 1) / movie.frames.length) * 100}%` }}
            transition={{ duration: 0.3 }} />
        </div>
        <span className="text-xs text-gray-500 font-mono w-12 text-right">
          {frameIdx < 0 ? 0 : frameIdx + 1}/{movie.frames.length}
        </span>
      </div>

      {/* Current frame */}
      <div className="px-5 py-4 min-h-[120px]">
        <AnimatePresence mode="wait">
          {frame ? (
            <motion.div key={frame.sequence}
              initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.3 }}>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
                  style={{ background: `${PHASE_COLOR[frame.kill_chain_phase] ?? "#6b7280"}22`,
                    color: PHASE_COLOR[frame.kill_chain_phase] ?? "#6b7280" }}>
                  {frame.sequence + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-medium mb-1">{frame.action}</p>
                  <div className="flex flex-wrap gap-2 text-[10px]">
                    <span className="px-1.5 py-0.5 rounded bg-white/5 text-gray-400">
                      {frame.kill_chain_phase.replace(/_/g, " ")}
                    </span>
                    <span className="px-1.5 py-0.5 rounded"
                      style={{ background: `${SEV[frame.severity_at_hop as keyof typeof SEV] ?? "#6b7280"}22`,
                        color: SEV[frame.severity_at_hop as keyof typeof SEV] ?? "#6b7280" }}>
                      {frame.severity_at_hop}
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-white/5 text-gray-400">
                      risk: {(frame.cumulative_risk * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>
              {/* Risk bar */}
              <div className="mt-3 bg-white/5 rounded-full h-1.5 overflow-hidden">
                <motion.div className="h-full rounded-full"
                  style={{ background: frame.cumulative_risk > 0.7 ? "#ef4444" : frame.cumulative_risk > 0.4 ? "#f59e0b" : "#06b6d4" }}
                  animate={{ width: `${frame.cumulative_risk * 100}%` }} transition={{ duration: 0.5 }} />
              </div>
            </motion.div>
          ) : (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="text-center text-gray-600 text-sm py-4">
              <Play className="w-8 h-8 mx-auto mb-2 opacity-30" />
              Press play to start the attack simulation
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

export default function AttackChainPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [chains, setChains] = useState<AttackChain[]>([]);
  const [selectedMovie, setSelectedMovie] = useState<AttackMovie | null>(null);
  const [loading, setLoading] = useState(false);
  const [discovering, setDiscovering] = useState(false);

  useEffect(() => {
    api.listRepositories().then((r) => { setRepos(r); if (r.length) setSelectedRepo(r[0].full_name); });
  }, []);

  useEffect(() => {
    if (!selectedRepo) return;
    setLoading(true); setSelectedMovie(null);
    api.listAttackChains(selectedRepo).then(setChains).finally(() => setLoading(false));
  }, [selectedRepo]);

  const discover = async () => {
    if (!selectedRepo) return;
    setDiscovering(true);
    const found = await api.discoverAttackChains(selectedRepo);
    setChains(found);
    setDiscovering(false);
  };

  const playChain = useCallback(async (chain: AttackChain) => {
    const movie = await api.getAttackMovie(chain);
    setSelectedMovie(movie);
  }, []);

  return (
    <div className="flex flex-col h-full bg-surface-950">
      {/* Header */}
      <div className="flex items-center gap-4 px-6 py-4 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-red-500/10 rounded-lg border border-red-500/20">
            <Swords className="w-5 h-5 text-red-400" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">Attack Chain Movie</h1>
            <p className="text-xs text-gray-500">Cinematic replay of multi-step attack paths</p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <select value={selectedRepo} onChange={(e) => setSelectedRepo(e.target.value)}
            className="bg-surface-900 border border-white/10 text-sm text-white rounded-lg px-3 py-2 focus:outline-none focus:border-red-400/50">
            {repos.map((r) => <option key={r.id} value={r.full_name}>{r.full_name}</option>)}
          </select>
          <button onClick={discover} disabled={discovering}
            className="flex items-center gap-2 px-3 py-2 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm hover:bg-red-500/30 transition-colors disabled:opacity-50">
            <Target className={`w-4 h-4 ${discovering ? "animate-spin" : ""}`} />
            Discover Chains
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Chain list */}
        <div className="w-80 flex-shrink-0 border-r border-white/5 overflow-y-auto">
          <div className="p-3 border-b border-white/5">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
              {chains.length} Attack Chains
            </h3>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-8 h-8 border-2 border-red-400/30 border-t-red-400 rounded-full animate-spin" />
            </div>
          ) : chains.length === 0 ? (
            <div className="text-center py-12 text-gray-600 text-sm px-4">
              <Swords className="w-10 h-10 mx-auto mb-3 opacity-20" />
              <p>No attack chains discovered</p>
              <p className="text-xs mt-1">Click "Discover Chains" to scan the graph</p>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {chains.map((c) => (
                <button key={c.id} onClick={() => playChain(c)}
                  className="w-full text-left p-4 hover:bg-white/5 transition-colors">
                  <div className="flex items-center gap-2 mb-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0"
                      style={{ color: c.severity_score > 3 ? "#ef4444" : c.severity_score > 1.5 ? "#f59e0b" : "#06b6d4" }} />
                    <span className="text-sm text-white font-medium truncate">
                      {c.entry_node?.label ?? "?"} → {c.target_node?.label ?? "?"}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-gray-500">
                    <span>{c.chain_length} hops</span>
                    <span>·</span>
                    <span className="font-mono" style={{ color: c.severity_score > 3 ? "#ef4444" : "#f59e0b" }}>
                      {c.severity_score.toFixed(2)}
                    </span>
                    {c.kill_chain_phases.length > 0 && (
                      <>
                        <span>·</span>
                        <span>{c.kill_chain_phases.length} phases</span>
                      </>
                    )}
                  </div>
                  {/* Mini kill chain */}
                  <div className="mt-2">
                    <KillChainBar phases={c.kill_chain_phases} current="" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Movie player */}
        <div className="flex-1 flex items-center justify-center p-8 overflow-y-auto">
          {selectedMovie ? (
            <div className="w-full max-w-2xl">
              <MoviePlayer movie={selectedMovie} onClose={() => setSelectedMovie(null)} />
            </div>
          ) : (
            <div className="text-center text-gray-600">
              <Swords className="w-16 h-16 mx-auto mb-4 opacity-20" />
              <p className="text-sm">Select an attack chain to watch the replay</p>
              <p className="text-xs mt-1">Each hop shows the attacker's progression through the kill chain</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
