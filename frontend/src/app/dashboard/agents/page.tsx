"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Bot,
  Brain,
  Code2,
  Zap,
  Shield,
  TrendingUp,
  Clock,
  Target,
  CheckCircle2,
} from "lucide-react";
import { api, type AgentInfo } from "@/lib/api";
import { cn } from "@/lib/utils";

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};
const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

const agentMeta: Record<string, { icon: string; color: string; phase: string }> = {
  threat_modeler:        { icon: "🎯", color: "#ff3366", phase: "Scan" },
  architecture_reviewer: { icon: "🏗️", color: "#8b5cf6", phase: "Scan" },
  code_intelligence:     { icon: "🔍", color: "#00f0ff", phase: "Scan" },
  dependency_intel:      { icon: "📦", color: "#ff6600", phase: "Scan" },
  secrets_detection:     { icon: "🔐", color: "#fbbf24", phase: "Scan" },
  infra_security:        { icon: "🖥️", color: "#10b981", phase: "Scan" },
  container_security:    { icon: "🐳", color: "#3b82f6", phase: "Scan" },
  cloud_security:        { icon: "☁️", color: "#6366f1", phase: "Scan" },
  api_security:          { icon: "🌐", color: "#ec4899", phase: "Scan" },
  business_logic:        { icon: "🧩", color: "#14b8a6", phase: "Scan" },
  llm_security:          { icon: "🤖", color: "#f59e0b", phase: "Scan" },
  compliance:            { icon: "📋", color: "#84cc16", phase: "Scan" },
  attack_simulation:     { icon: "⚔️", color: "#ef4444", phase: "Action" },
  auto_patcher:          { icon: "🔧", color: "#22c55e", phase: "Action" },
  regression_tester:     { icon: "🧪", color: "#a855f7", phase: "Action" },
  documentation:         { icon: "📝", color: "#06b6d4", phase: "Action" },
  deployment_approval:   { icon: "✅", color: "#10b981", phase: "Action" },
  learning_agent:        { icon: "📚", color: "#f97316", phase: "Action" },
};

const tierInfo: Record<string, { label: string; icon: any; color: string }> = {
  reasoning:   { label: "Reasoning", icon: Brain, color: "#8b5cf6" },
  code:        { label: "Code", icon: Code2, color: "#00f0ff" },
  lightweight: { label: "Lightweight", icon: Zap, color: "#fbbf24" },
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAgents();
  }, []);

  async function loadAgents() {
    try {
      const data = await api.listAgents();
      setAgents(data);
    } catch {
      // Build demo from metadata
      setAgents(
        Object.entries(agentMeta).map(([name, meta]) => ({
          name,
          purpose: `Security analysis — ${meta.phase} phase`,
          model_tier: name.includes("approval") || name.includes("threat") || name.includes("attack") || name.includes("learning") || name.includes("business") || name.includes("llm")
            ? "reasoning"
            : name.includes("secrets") || name.includes("dependency") || name.includes("compliance")
            ? "lightweight"
            : "code",
          reasoning_strategy: name.includes("threat") || name.includes("attack") || name.includes("approval") || name.includes("business") || name.includes("llm") || name.includes("arch")
            ? "tree_of_thought"
            : "chain_of_thought",
          inputs: ["code_diff"],
          outputs: ["findings"],
          metrics: {
            total_runs: Math.floor(Math.random() * 50),
            success_rate: 0.85 + Math.random() * 0.15,
            total_findings: Math.floor(Math.random() * 100),
          },
        }))
      );
    } finally {
      setLoading(false);
    }
  }

  const scanAgents = agents.filter((a) => agentMeta[a.name]?.phase === "Scan");
  const actionAgents = agents.filter((a) => agentMeta[a.name]?.phase === "Action");

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Bot className="w-10 h-10 text-cyber-cyan animate-pulse" />
      </div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-8"
    >
      {/* Header */}
      <motion.div variants={itemVariants}>
        <h1 className="text-xl font-bold text-gray-100">
          Security Agents
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          {agents.length} autonomous agents across 2 execution phases
        </p>
      </motion.div>

      {/* Pipeline Visualization */}
      <motion.div variants={itemVariants} className="glass-card p-6">
        <h3 className="text-xs text-gray-500 uppercase tracking-wider mb-4">
          Pipeline Architecture
        </h3>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="px-3 py-1.5 rounded-lg bg-cyber-cyan/10 border border-cyber-cyan/20 text-cyber-cyan text-xs font-medium">
            Indexing
          </div>
          <span className="text-gray-600">→</span>
          <div className="px-3 py-1.5 rounded-lg bg-cyber-purple/10 border border-cyber-purple/20 text-cyber-purple text-xs font-medium">
            Knowledge Graph
          </div>
          <span className="text-gray-600">→</span>
          <div className="px-3 py-1.5 rounded-lg bg-cyber-green/10 border border-cyber-green/20 text-cyber-green text-xs font-medium">
            Parallel Scan (12 agents)
          </div>
          <span className="text-gray-600">→</span>
          <div className="px-3 py-1.5 rounded-lg bg-cyber-orange/10 border border-cyber-orange/20 text-cyber-orange text-xs font-medium">
            Attack Simulation
          </div>
          <span className="text-gray-600">→</span>
          <div className="px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
            Patch → Test → Verify
          </div>
          <span className="text-gray-600">→</span>
          <div className="px-3 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-medium">
            Approve / Block
          </div>
        </div>
      </motion.div>

      {/* Scan Phase */}
      <div>
        <motion.h2
          variants={itemVariants}
          className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4"
        >
          🔍 Scan Phase — Parallel Execution
        </motion.h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scanAgents.map((agent) => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </div>
      </div>

      {/* Action Phase */}
      <div>
        <motion.h2
          variants={itemVariants}
          className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4"
        >
          ⚡ Action Phase — Sequential Execution
        </motion.h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {actionAgents.map((agent) => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </div>
      </div>
    </motion.div>
  );
}

function AgentCard({ agent }: { agent: AgentInfo }) {
  const meta = agentMeta[agent.name] || { icon: "🤖", color: "#6b7280", phase: "?" };
  const tier = tierInfo[agent.model_tier] || tierInfo.code;
  const TierIcon = tier.icon;

  return (
    <motion.div
      variants={itemVariants}
      className="glass-card-hover p-5 group cursor-pointer"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center text-lg"
            style={{
              background: `${meta.color}15`,
              border: `1px solid ${meta.color}30`,
            }}
          >
            {meta.icon}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-200 group-hover:text-white transition-colors">
              {agent.name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            </h3>
            <div className="flex items-center gap-1.5 mt-0.5">
              <TierIcon className="w-3 h-3" style={{ color: tier.color }} />
              <span className="text-[10px]" style={{ color: tier.color }}>
                {tier.label}
              </span>
              <span className="text-gray-700 text-[10px]">•</span>
              <span className="text-[10px] text-gray-500">
                {agent.reasoning_strategy.replace(/_/g, " ")}
              </span>
            </div>
          </div>
        </div>
      </div>

      <p className="text-xs text-gray-500 mb-3">{agent.purpose}</p>

      <div className="flex items-center gap-4 text-xs text-gray-500">
        <div className="flex items-center gap-1">
          <Target className="w-3 h-3" />
          <span>{agent.metrics.total_runs} runs</span>
        </div>
        <div className="flex items-center gap-1">
          <CheckCircle2 className="w-3 h-3 text-cyber-green" />
          <span>{(agent.metrics.success_rate * 100).toFixed(0)}%</span>
        </div>
        <div className="flex items-center gap-1">
          <Shield className="w-3 h-3" />
          <span>{agent.metrics.total_findings} findings</span>
        </div>
      </div>

      {/* Success rate bar */}
      <div className="mt-3 progress-bar">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${agent.metrics.success_rate * 100}%`,
            backgroundColor: meta.color,
          }}
        />
      </div>
    </motion.div>
  );
}
