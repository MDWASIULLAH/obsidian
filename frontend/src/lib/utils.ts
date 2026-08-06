import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDuration(seconds: number | null): string {
  if (!seconds) return "—";
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs}s`;
}

export function severityColor(severity: string): string {
  const colors: Record<string, string> = {
    critical: "text-cyber-red",
    high: "text-cyber-orange",
    medium: "text-cyber-yellow",
    low: "text-blue-400",
    info: "text-gray-400",
  };
  return colors[severity] || "text-gray-400";
}

export function severityBadge(severity: string): string {
  return `badge-${severity}`;
}

export function statusColor(status: string): string {
  const colors: Record<string, string> = {
    completed: "text-cyber-green",
    scanning: "text-cyber-cyan",
    queued: "text-gray-400",
    failed: "text-cyber-red",
    cancelled: "text-gray-500",
  };
  return colors[status] || "text-gray-400";
}

export function scoreColor(score: number): string {
  if (score >= 80) return "text-cyber-green";
  if (score >= 60) return "text-cyber-yellow";
  if (score >= 40) return "text-cyber-orange";
  return "text-cyber-red";
}

export function scoreGradient(score: number): string {
  if (score >= 80) return "from-emerald-500 to-cyan-500";
  if (score >= 60) return "from-yellow-500 to-orange-500";
  if (score >= 40) return "from-orange-500 to-red-500";
  return "from-red-500 to-rose-600";
}
