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
    critical: "text-red-500",
    high: "text-orange-500",
    medium: "text-amber-500",
    low: "text-blue-500",
    info: "text-slate-400",
  };
  return colors[severity] || "text-slate-400";
}

export function severityBadge(severity: string): string {
  return `badge-${severity}`;
}

export function statusColor(status: string): string {
  const colors: Record<string, string> = {
    completed: "text-teal-500",
    scanning: "text-blue-500",
    queued: "text-slate-400",
    failed: "text-red-500",
    cancelled: "text-slate-500",
  };
  return colors[status] || "text-slate-400";
}

export function scoreColor(score: number): string {
  if (score >= 80) return "text-teal-500";
  if (score >= 60) return "text-amber-500";
  if (score >= 40) return "text-orange-500";
  return "text-red-500";
}

export function scoreGradient(score: number): string {
  if (score >= 80) return "from-teal-500 to-emerald-500";
  if (score >= 60) return "from-amber-500 to-orange-500";
  if (score >= 40) return "from-orange-500 to-red-500";
  return "from-red-500 to-rose-600";
}
