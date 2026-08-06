"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, CheckCircle, Github } from "lucide-react";
import { useSession } from "next-auth/react";

export default function SetupPage() {
  const [isProvisioning, setIsProvisioning] = useState(false);
  const router = useRouter();
  const { data: session } = useSession();

  const handleAuthorize = async () => {
    setIsProvisioning(true);
    try {
      await fetch("http://localhost:8000/api/v1/onboarding/provision-security-center", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: (session as any)?.userId || "demo-user-id" })
      });
      localStorage.setItem("obsidian_onboarded", "true");
      router.push("/dashboard");
    } catch (e) {
      console.error(e);
      setIsProvisioning(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-950 flex flex-col items-center justify-center p-4">
      <div className="glass-card p-10 max-w-2xl w-full">
        <div className="flex items-center gap-4 mb-8 pb-8 border-b border-surface-800">
          <div className="w-12 h-12 bg-primary-500/10 rounded-xl flex items-center justify-center text-primary-500">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-100">Authorize OBSIDIAN Autonomous Agent</h1>
            <p className="text-gray-400">Deploy the 24/7 security engine to your GitHub account.</p>
          </div>
        </div>

        <div className="space-y-6 mb-10">
          <p className="text-gray-300">
            To provide true autonomous security, OBSIDIAN needs your permission to create a central control repository on your GitHub account.
          </p>
          
          <div className="bg-surface-900 rounded-lg p-5 border border-surface-800">
            <h3 className="font-semibold text-gray-200 mb-4 flex items-center gap-2">
              <Github className="w-5 h-5 text-gray-400" /> What will happen?
            </h3>
            <ul className="space-y-3">
              <li className="flex gap-3 text-sm text-gray-400">
                <CheckCircle className="w-5 h-5 text-teal-500 shrink-0" />
                <span>A new private repository named <strong>obsidian-security-center</strong> will be created on your GitHub account.</span>
              </li>
              <li className="flex gap-3 text-sm text-gray-400">
                <CheckCircle className="w-5 h-5 text-teal-500 shrink-0" />
                <span>A robust 24/7 <strong>Python agent</strong> and GitHub Actions workflow will be committed to this repository.</span>
              </li>
              <li className="flex gap-3 text-sm text-gray-400">
                <CheckCircle className="w-5 h-5 text-teal-500 shrink-0" />
                <span>The agent will autonomously clone, scan, and monitor your repositories, pushing real-time findings to this dashboard.</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="flex justify-end gap-4">
          <button 
            onClick={() => router.push("/")}
            className="px-6 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:text-gray-200 hover:bg-surface-800 transition-colors"
          >
            Cancel
          </button>
          <button 
            onClick={handleAuthorize}
            disabled={isProvisioning}
            className="px-6 py-2.5 rounded-lg text-sm font-medium bg-primary-500 text-surface-950 hover:bg-primary-400 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isProvisioning ? (
              <>
                <div className="w-4 h-4 border-2 border-surface-950/30 border-t-surface-950 rounded-full animate-spin" />
                Deploying Engine...
              </>
            ) : (
              "Authorize & Deploy"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
