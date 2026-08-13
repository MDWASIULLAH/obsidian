"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  GitBranch,
  Search,
  Star,
  GitFork,
  Lock,
  Globe,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface GitHubRepo {
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
  private: boolean;
  stargazers_count: number;
  forks_count: number;
  updated_at: string;
  created_at: string;
  html_url: string;
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.04 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

const langColors: Record<string, string> = {
  Python: "#3572A5", TypeScript: "#3178c6", JavaScript: "#f1e05a", Go: "#00ADD8",
  Rust: "#dea584", Java: "#b07219", HCL: "#844FBA", Ruby: "#701516", C: "#555555",
  "C++": "#f34b7d", "C#": "#178600", PHP: "#4F5D95", Swift: "#F05138", Kotlin: "#A97BFF",
  Dart: "#00B4AB", HTML: "#e34c26", CSS: "#563d7c", Shell: "#89e051", Jupyter: "#DA5B0B", Vue: "#41b883",
};

function scoreColor(score: number): string {
  if (score === 0) return "text-gray-500";
  if (score >= 85) return "text-teal-400";
  if (score >= 70) return "text-yellow-400";
  if (score >= 50) return "text-orange-400";
  return "text-red-400";
}

function timeAgo(dateStr: string): string {
  const diffMs = Math.max(0, Date.now() - new Date(dateStr).getTime());
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

export default function RepositoriesPage() {
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "public" | "private">("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRepos();
  }, []);

  async function loadRepos() {
    setLoading(true);
    try {
      const res = await fetch("/api/github/repos", { cache: "no-store" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setRepos([]);
        setError(typeof data.error === "string" ? data.error : `HTTP_${res.status}`);
        return;
      }
      setRepos(Array.isArray(data.repos) ? data.repos : []);
      setError(null);
    } catch (err) {
      console.error("Failed to load repos:", err);
      setRepos([]);
      setError("NETWORK_ERROR");
    } finally {
      setLoading(false);
    }
  }

  const filteredRepos = repos.filter((repo) => {
    const query = searchQuery.toLowerCase();
    const matchesSearch = !query || repo.full_name.toLowerCase().includes(query) ||
      (repo.description || "").toLowerCase().includes(query) ||
      (repo.language || "").toLowerCase().includes(query);
    const matchesFilter = filter === "all" || (filter === "private" && repo.private) || (filter === "public" && !repo.private);
    return matchesSearch && matchesFilter;
  });

  if (loading) {
    return <div className="flex flex-col items-center justify-center h-[60vh] gap-4"><RefreshCw className="w-8 h-8 text-primary-500 animate-spin" /><p className="text-sm text-gray-400">Loading your GitHub repositories...</p></div>;
  }

  const authError = error === "AUTH_REQUIRED" || error === "GITHUB_TOKEN_INVALID";

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={itemVariants} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">Your Repositories</h1>
          <p className="text-sm text-gray-500 mt-1">{repos.length} repositories from your GitHub account</p>
        </div>
        <button onClick={loadRepos} disabled={loading} className="flex items-center gap-2 px-4 py-2 bg-surface-800 border border-surface-700 text-gray-300 rounded-lg text-sm font-medium hover:bg-surface-700 transition-all disabled:opacity-50">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </motion.div>

      <motion.div variants={itemVariants} className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search repositories..." className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-primary-500/30" />
        </div>
        <div className="flex gap-1 bg-surface-800/50 rounded-lg p-1 border border-surface-700">
          {(["all", "public", "private"] as const).map((f) => <button key={f} onClick={() => setFilter(f)} className={cn("px-3 py-1.5 rounded-md text-xs font-medium transition-colors capitalize", filter === f ? "bg-surface-700 text-gray-100" : "text-gray-400 hover:text-gray-200")}>{f}</button>)}
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        {filteredRepos.map((repo) => (
          <motion.a key={repo.id} variants={itemVariants} href={repo.html_url} target="_blank" rel="noopener noreferrer" className="glass-card-hover p-5 group block">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                <GitBranch className="w-5 h-5 text-gray-500 shrink-0" />
                <div className="min-w-0"><h3 className="text-sm font-semibold text-gray-200 group-hover:text-primary-400 transition-colors truncate">{repo.name}</h3><p className="text-xs text-gray-500">{repo.owner}</p></div>
              </div>
              <div className="flex items-center gap-1.5 shrink-0 ml-2">
                {repo.private ? <Lock className="w-3.5 h-3.5 text-yellow-500" /> : <Globe className="w-3.5 h-3.5 text-gray-500" />}
                <div className={cn("text-lg font-bold font-mono", scoreColor(repo.security_score))}>{repo.security_score === 0 ? "—" : repo.security_score}</div>
              </div>
            </div>
            {repo.description && <p className="text-xs text-gray-500 mb-3 line-clamp-2">{repo.description}</p>}
            <div className="flex items-center gap-4 text-xs text-gray-500">
              {repo.language && <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: langColors[repo.language] || "#6b7280" }} /><span>{repo.language}</span></div>}
              <div className="flex items-center gap-1"><Star className="w-3 h-3" /><span>{repo.stargazers_count}</span></div>
              <div className="flex items-center gap-1"><GitFork className="w-3 h-3" /><span>{repo.forks_count}</span></div>
              <div className="ml-auto text-xs text-gray-600">{timeAgo(repo.updated_at)}</div>
            </div>
            <div className="mt-3 progress-bar"><div className="progress-bar-fill" style={{ width: `${Math.max(0, Math.min(100, repo.security_score))}%` }} /></div>
          </motion.a>
        ))}
      </div>

      {filteredRepos.length === 0 && (
        <div className="text-center py-20">
          <GitBranch className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 text-lg font-medium">
            {authError ? "GitHub session needs refresh" : error ? "GitHub repositories are unavailable" : searchQuery ? "No repositories found" : "No repositories found"}
          </p>
          <p className="text-xs text-gray-500 mt-1 mb-6">
            {authError ? "Your GitHub login is valid, but repository access is not present in the current session." : error ? "Check the GitHub connection and try again." : searchQuery ? "Try a different search query" : "No repositories are available to this GitHub account."}
          </p>
          {authError && <button onClick={() => { window.location.href = "/api/auth/signout?callbackUrl=/"; }} className="px-6 py-3 bg-primary-500 text-surface-950 rounded-lg font-semibold hover:bg-primary-400 transition-colors">Sign Out & Re-Login</button>}
          {!authError && error && <button onClick={loadRepos} className="px-5 py-2.5 bg-surface-800 border border-surface-700 text-gray-300 rounded-lg text-sm font-medium hover:bg-surface-700">Retry</button>}
        </div>
      )}
    </motion.div>
  );
}
