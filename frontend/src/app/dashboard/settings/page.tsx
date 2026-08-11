"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useSession, signOut } from "next-auth/react";
import {
  User,
  Shield,
  Bell,
  Key,
  Globe,
  LogOut,
  Check,
  ExternalLink,
  Github,
  Cloud,
} from "lucide-react";

const tabs = [
  { id: "profile", label: "Profile", icon: User },
  { id: "security", label: "Security", icon: Shield },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "api", label: "API Keys", icon: Key },
  { id: "integrations", label: "Integrations", icon: Globe },
];

const notificationDefaults = {
  critical: true,
  scans: true,
  patches: false,
  deployments: true,
};

export default function SettingsPage() {
  const { data: session } = useSession();
  const [activeTab, setActiveTab] = useState("profile");
  const [notifications, setNotifications] = useState(notificationDefaults);

  const toggleNotification = (key: keyof typeof notifications) => {
    setNotifications((current) => ({ ...current, [key]: !current[key] }));
  };

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-xl font-bold text-gray-100">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">Manage your account, security preferences, and integrations</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-5 lg:gap-6 min-w-0">
        <div className="lg:w-56 lg:shrink-0">
          <div className="flex lg:flex-col gap-1 overflow-x-auto lg:overflow-visible pb-1 lg:pb-0 [scrollbar-width:thin]">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`shrink-0 flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm transition-all whitespace-nowrap ${
                    activeTab === tab.id
                      ? "bg-surface-800 text-gray-100 font-medium border border-surface-700"
                      : "text-gray-400 hover:text-gray-200 hover:bg-surface-800/50"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          <button
            type="button"
            onClick={() => signOut({ callbackUrl: "/" })}
            className="mt-3 w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-all border border-transparent"
          >
            <LogOut className="w-4 h-4" />
            Sign Out of GitHub
          </button>
        </div>

        <div className="flex-1 min-w-0">
          {activeTab === "profile" && (
            <div className="glass-card p-4 sm:p-6 space-y-6">
              <h2 className="text-lg font-semibold text-gray-100">Profile</h2>
              <div className="flex flex-col sm:flex-row sm:items-center gap-4 p-4 bg-surface-800/50 rounded-lg border border-surface-700">
                <img src={session?.user?.image || `https://avatar.vercel.sh/${session?.user?.name || "user"}`} alt="GitHub profile" className="w-16 h-16 rounded-full border-2 border-surface-600" />
                <div className="min-w-0">
                  <p className="text-lg font-semibold text-gray-100 truncate">{session?.user?.name || "User"}</p>
                  <p className="text-sm text-gray-400 truncate">{session?.user?.email || "No email"}</p>
                  <p className="text-xs text-gray-500 mt-1">Provider: GitHub</p>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">Display Name</label>
                  <input type="text" value={session?.user?.name || ""} readOnly className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-200 focus:outline-none" />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">Email</label>
                  <input type="email" value={session?.user?.email || ""} readOnly className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-200 focus:outline-none" />
                </div>
              </div>
              <a href="https://github.com/settings/profile" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-4 py-2.5 bg-surface-800 border border-surface-700 rounded-lg text-sm text-gray-300 hover:bg-surface-700 transition-colors">
                Manage GitHub profile <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          )}

          {activeTab === "security" && (
            <div className="glass-card p-4 sm:p-6 space-y-6">
              <h2 className="text-lg font-semibold text-gray-100">Security Settings</h2>
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 bg-surface-800/50 rounded-lg border border-surface-700">
                  <div><p className="text-sm font-medium text-gray-200">Two-Factor Authentication</p><p className="text-xs text-gray-400 mt-0.5">Managed through your GitHub account</p></div>
                  <a href="https://github.com/settings/security" target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium text-primary-400 bg-primary-500/10 rounded-lg hover:bg-primary-500/20">Manage on GitHub <ExternalLink className="w-3 h-3" /></a>
                </div>
                <div className="flex items-center justify-between gap-4 p-4 bg-surface-800/50 rounded-lg border border-surface-700">
                  <div><p className="text-sm font-medium text-gray-200">Active Session</p><p className="text-xs text-gray-400 mt-0.5">Currently signed in on this device</p></div>
                  <div className="flex items-center gap-1.5 text-xs text-teal-400 shrink-0"><Check className="w-3.5 h-3.5" />Active</div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "notifications" && (
            <div className="glass-card p-4 sm:p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-100 mb-2">Notification Preferences</h2>
              {[
                ["critical", "Critical Vulnerabilities", "Alert on severity 9+ findings"],
                ["scans", "Scan Completion", "Notify when a security scan finishes"],
                ["patches", "Auto-Patch PRs", "Notify when patches are generated"],
                ["deployments", "Deployment Approvals", "GO/NO-GO decision notifications"],
              ].map(([key, label, desc]) => {
                const enabled = notifications[key as keyof typeof notifications];
                return (
                  <button key={key} type="button" onClick={() => toggleNotification(key as keyof typeof notifications)} className="w-full flex items-center justify-between gap-4 p-4 bg-surface-800/50 rounded-lg border border-surface-700 text-left hover:bg-surface-800 transition-colors">
                    <div><p className="text-sm font-medium text-gray-200">{label}</p><p className="text-xs text-gray-400 mt-0.5">{desc}</p></div>
                    <span className={`w-10 h-5 rounded-full relative shrink-0 transition-colors ${enabled ? "bg-primary-500" : "bg-surface-700"}`}><span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${enabled ? "left-5" : "left-0.5"}`} /></span>
                  </button>
                );
              })}
            </div>
          )}

          {activeTab === "api" && (
            <div className="glass-card p-4 sm:p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-100">API Keys</h2>
              <p className="text-sm text-gray-400">API key management is not connected to a backend endpoint yet.</p>
              <div className="p-4 bg-yellow-500/5 border border-yellow-500/20 rounded-lg">
                <p className="text-sm text-yellow-300">No fake API key is shown. Connect your API-key service before enabling generation or regeneration.</p>
              </div>
            </div>
          )}

          {activeTab === "integrations" && (
            <div className="glass-card p-4 sm:p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-100">Integrations</h2>
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 bg-surface-800/50 rounded-lg border border-surface-700">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 bg-gray-800 rounded-lg flex items-center justify-center shrink-0"><Github className="w-6 h-6 text-white" /></div>
                    <div className="min-w-0"><p className="text-sm font-medium text-gray-200">GitHub</p><p className="text-xs text-gray-400 truncate">Connected as {session?.user?.name || "user"}</p></div>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-teal-400 bg-teal-500/10 px-3 py-1.5 rounded-full w-fit"><Check className="w-3.5 h-3.5" />Connected</div>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 bg-surface-800/50 rounded-lg border border-surface-700">
                  <div className="flex items-center gap-3"><div className="w-10 h-10 bg-gray-800 rounded-lg flex items-center justify-center"><Cloud className="w-5 h-5 text-white" /></div><div><p className="text-sm font-medium text-gray-200">Vercel</p><p className="text-xs text-gray-400">Deployment is managed by the connected Vercel project</p></div></div>
                  <a href="https://vercel.com/dashboard" target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-surface-700 text-gray-300 rounded-lg hover:bg-surface-600">Open Vercel <ExternalLink className="w-3 h-3" /></a>
                </div>

                {["Slack", "Jira", "PagerDuty"].map((service) => (
                  <div key={service} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 bg-surface-800/50 rounded-lg border border-surface-700">
                    <div className="flex items-center gap-3"><div className="w-10 h-10 bg-surface-800 rounded-lg flex items-center justify-center"><Globe className="w-5 h-5 text-gray-500" /></div><div><p className="text-sm font-medium text-gray-200">{service}</p><p className="text-xs text-gray-400">Integration endpoint not configured</p></div></div>
                    <span className="px-3 py-1.5 text-xs font-medium text-gray-500 bg-surface-800 rounded-lg w-fit">Not configured</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
