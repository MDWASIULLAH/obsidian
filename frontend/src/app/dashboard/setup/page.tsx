"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Shield, CheckCircle, Github, RefreshCw, AlertTriangle } from "lucide-react";
import { useSession } from "next-auth/react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://obsidian-backend-gute.onrender.com";

export default function SetupPage() {
  const [isWorking, setIsWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncSummary, setSyncSummary] = useState<string | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // Enforce session via NextAuth
  const { data: session, status } = useSession({ required: true });
  
  const userId = (session as any)?.userId as string | undefined;
  const installationId = searchParams.get("installation_id");

  useEffect(() => {
    // Only attempt sync if we have all needed data and haven't already succeeded
    if (!installationId || !userId || isWorking || syncSummary) return;

    const syncInstallation = async () => {
      setIsWorking(true);
      setError(null);
      try {
        const response = await fetch(`${API_BASE}/api/v1/onboarding/github-app/sync-installation`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            installation_id: Number(installationId),
            user_id: userId,
          }),
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || "GitHub App installation sync failed");
        }

        localStorage.setItem("obsidian_onboarded", "true");
        setSyncSummary(
          `${data.repositories_authorized} repositories authorized for ${data.account}`,
        );
        setTimeout(() => router.push("/dashboard"), 1000);
      } catch (err: any) {
        setError(err.message || "Could not sync GitHub App installation");
      } finally {
        setIsWorking(false);
      }
    };

    syncInstallation();
  }, [installationId, userId, isWorking, syncSummary, router]);

  const handleInstall = async () => {
    setIsWorking(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/v1/onboarding/github-app/install-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "GitHub App install URL is not configured");
      }
      window.location.href = data.install_url;
    } catch (err: any) {
      setError(err.message || "Could not start GitHub App installation");
      setIsWorking(false);
    }
  };

  // 1. Session Loading State
  if (status === "loading") {
    return (
      <div className="min-h-screen bg-surface-950 flex flex-col items-center justify-center p-4">
        <RefreshCw className="w-8 h-8 text-primary-500 animate-spin" />
        <p className="mt-4 text-gray-400">Authenticating session...</p>
      </div>
    );
  }

  // 2. Authentication Failure / Missing Backend ID State
  if (status === "authenticated" && !userId) {
    return (
      <div className="min-h-screen bg-surface-950 flex flex-col items-center justify-center p-4">
        <div className="glass-card p-10 max-w-lg w-full text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-100 mb-2">Authentication Error</h2>
          <p className="text-gray-400 mb-6">
            Your GitHub login was successful, but the backend system failed to synchronize your account. This is usually a temporary issue.
          </p>
          <button
            onClick={() => router.push("/")}
            className="px-6 py-2.5 rounded-lg text-sm font-medium bg-surface-800 text-gray-200 hover:bg-surface-700 transition-colors"
          >
            Return Home and Try Again
          </button>
        </div>
      </div>
    );
  }

  // 3 & 4 & 5. Ready to Install / Syncing Installation
  return (
    <div className="min-h-screen bg-surface-950 flex flex-col items-center justify-center p-4">
      <div className="glass-card p-10 max-w-2xl w-full">
        <div className="flex items-center gap-4 mb-8 pb-8 border-b border-surface-800">
          <div className="w-12 h-12 bg-primary-500/10 rounded-xl flex items-center justify-center text-primary-500">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-100">Install OBSIDIAN GitHub App</h1>
            <p className="text-gray-400">Authorize repositories for continuous backend monitoring.</p>
          </div>
        </div>

        <div className="space-y-6 mb-10">
          <p className="text-gray-300">
            OBSIDIAN runs inside its own backend. It listens to GitHub webhooks, imports authorized repositories, queues scans, and streams live progress without committing monitoring files to your repositories.
          </p>

          <div className="bg-surface-900 rounded-lg p-5 border border-surface-800">
            <h3 className="font-semibold text-gray-200 mb-4 flex items-center gap-2">
              <Github className="w-5 h-5 text-gray-400" /> What happens next?
            </h3>
            <ul className="space-y-3">
              <li className="flex gap-3 text-sm text-gray-400">
                <CheckCircle className="w-5 h-5 text-teal-500 shrink-0" />
                <span>Install the GitHub App on selected repositories or the whole account.</span>
              </li>
              <li className="flex gap-3 text-sm text-gray-400">
                <CheckCircle className="w-5 h-5 text-teal-500 shrink-0" />
                <span>OBSIDIAN imports authorized public, private, and organization repositories automatically.</span>
              </li>
              <li className="flex gap-3 text-sm text-gray-400">
                <CheckCircle className="w-5 h-5 text-teal-500 shrink-0" />
                <span>GitHub webhooks trigger the backend pipeline on pushes, pull requests, alerts, releases, workflow events, and repository changes.</span>
              </li>
            </ul>
          </div>

          {syncSummary && (
            <div className="rounded-lg border border-teal-500/30 bg-teal-500/10 px-4 py-3 text-sm text-teal-200 flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-teal-500 shrink-0" />
              {syncSummary}
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200 flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
              {error}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-4">
          <button
            onClick={() => router.push("/")}
            className="px-6 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:text-gray-200 hover:bg-surface-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleInstall}
            disabled={isWorking || !userId || !!syncSummary}
            className="px-6 py-2.5 rounded-lg text-sm font-medium bg-primary-500 text-surface-950 hover:bg-primary-400 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isWorking ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                {installationId ? "Syncing Installation..." : "Loading GitHub..."}
              </>
            ) : syncSummary ? (
              <>
                <CheckCircle className="w-4 h-4" />
                Installed
              </>
            ) : (
              <>
                <Github className="w-4 h-4" />
                Install GitHub App
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
