"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  GitBranch,
  Plus,
  Shield,
  ExternalLink,
  Search,
  Activity,
  AlertTriangle,
} from "lucide-react";
import { api, type Repository } from "@/lib/api";
import { cn, formatDate, scoreColor } from "@/lib/utils";

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

export default function RepositoriesPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newRepo, setNewRepo] = useState("");
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    loadRepos();
  }, []);

  async function loadRepos() {
    try {
      const data = await api.listRepositories();
      setRepos(data);
    } catch (err) {
      console.error("Failed to load repos:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd() {
    if (!newRepo.trim()) return;
    setAdding(true);
    try {
      const repo = await api.addRepository(newRepo.trim());
      setRepos((prev) => [repo, ...prev]);
    } catch (err) {
      console.error("Failed to add repo:", err);
    } finally {
      setNewRepo("");
      setShowAdd(false);
      setAdding(false);
    }
  }

  const langColors: Record<string, string> = {
    Python: "#3572A5",
    TypeScript: "#3178c6",
    JavaScript: "#f1e05a",
    Go: "#00ADD8",
    Rust: "#dea584",
    Java: "#b07219",
    HCL: "#844FBA",
    Ruby: "#701516",
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Shield className="w-10 h-10 text-cyber-cyan animate-pulse" />
      </div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      {/* Header */}
      <motion.div
        variants={itemVariants}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-xl font-bold text-gray-100">
            Tracked Repositories
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {repos.length} repositories under continuous security monitoring
          </p>
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="flex items-center gap-2 px-4 py-2 bg-cyber-cyan/10 border border-cyber-cyan/20 text-cyber-cyan rounded-lg text-sm font-medium hover:bg-cyber-cyan/20 transition-all"
        >
          <Plus className="w-4 h-4" />
          Add Repository
        </button>
      </motion.div>

      {/* Add Modal */}
      {showAdd && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="glass-card p-5"
        >
          <h3 className="text-sm font-medium text-gray-200 mb-3">
            Add GitHub Repository
          </h3>
          <div className="flex gap-3">
            <input
              type="text"
              value={newRepo}
              onChange={(e) => setNewRepo(e.target.value)}
              placeholder="owner/repository-name"
              className="flex-1 px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyber-cyan/30"
            />
            <button
              onClick={handleAdd}
              disabled={adding || !newRepo.trim()}
              className="px-6 py-2.5 bg-gradient-to-r from-cyber-cyan to-cyber-green text-surface-900 rounded-lg text-sm font-semibold disabled:opacity-50 hover:shadow-lg hover:shadow-cyber-cyan/20 transition-all"
            >
              {adding ? "Adding..." : "Track"}
            </button>
          </div>
        </motion.div>
      )}

      {/* Repository Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        {repos.map((repo) => (
          <motion.a
            key={repo.id}
            variants={itemVariants}
            href={`/dashboard/repositories/${repo.id}`}
            className="glass-card-hover p-5 group block"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <GitBranch className="w-5 h-5 text-gray-500" />
                <div>
                  <h3 className="text-sm font-semibold text-gray-200 group-hover:text-cyber-cyan transition-colors">
                    {repo.name}
                  </h3>
                  <p className="text-xs text-gray-500">{repo.owner}</p>
                </div>
              </div>
              <div
                className={cn(
                  "text-lg font-bold font-mono",
                  scoreColor(repo.security_score)
                )}
              >
                {repo.security_score}
              </div>
            </div>

            {repo.description && (
              <p className="text-xs text-gray-500 mb-3 line-clamp-2">
                {repo.description}
              </p>
            )}

            <div className="flex items-center gap-4 text-xs text-gray-500">
              {repo.language && (
                <div className="flex items-center gap-1.5">
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{
                      backgroundColor:
                        langColors[repo.language] || "#6b7280",
                    }}
                  />
                  <span>{repo.language}</span>
                </div>
              )}
              <div className="flex items-center gap-1">
                <Activity className="w-3 h-3" />
                <span>{repo.total_scans} scans</span>
              </div>
              <div className="flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                <span>{repo.total_findings} findings</span>
              </div>
            </div>

            <div className="mt-3 progress-bar">
              <div
                className="progress-bar-fill"
                style={{ width: `${repo.security_score}%` }}
              />
            </div>
          </motion.a>
        ))}
      </div>
    </motion.div>
  );
}
