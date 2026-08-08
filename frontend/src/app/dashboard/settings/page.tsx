"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useSession, signOut } from "next-auth/react";
import {
  Settings,
  User,
  Shield,
  Bell,
  Key,
  Globe,
  LogOut,
  Check,
  ExternalLink,
} from "lucide-react";

export default function SettingsPage() {
  const { data: session } = useSession();
  const [activeTab, setActiveTab] = useState("profile");

  const tabs = [
    { id: "profile", label: "Profile", icon: User },
    { id: "security", label: "Security", icon: Shield },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "api", label: "API Keys", icon: Key },
    { id: "integrations", label: "Integrations", icon: Globe },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div>
        <h1 className="text-xl font-bold text-gray-100">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage your account, security preferences, and integrations
        </p>
      </div>

      <div className="flex gap-6">
        {/* Settings Sidebar */}
        <div className="w-56 space-y-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm transition-all ${
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

          <div className="pt-4 mt-4 border-t border-surface-800">
            <button
              onClick={() => signOut({ callbackUrl: "/" })}
              className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-all"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </button>
          </div>
        </div>

        {/* Settings Content */}
        <div className="flex-1">
          {activeTab === "profile" && (
            <div className="glass-card p-6 space-y-6">
              <h2 className="text-lg font-semibold text-gray-100">Profile</h2>

              <div className="flex items-center gap-4 p-4 bg-surface-800/50 rounded-lg border border-surface-700">
                <img
                  src={
                    session?.user?.image ||
                    `https://avatar.vercel.sh/${session?.user?.name}`
                  }
                  alt="Avatar"
                  className="w-16 h-16 rounded-full border-2 border-surface-600"
                />
                <div>
                  <p className="text-lg font-semibold text-gray-100">
                    {session?.user?.name || "User"}
                  </p>
                  <p className="text-sm text-gray-400">
                    {session?.user?.email || "No email"}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Provider: GitHub
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">
                    Display Name
                  </label>
                  <input
                    type="text"
                    defaultValue={session?.user?.name || ""}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-primary-500/30"
                    readOnly
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">
                    Email
                  </label>
                  <input
                    type="email"
                    defaultValue={session?.user?.email || ""}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-primary-500/30"
                    readOnly
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === "security" && (
            <div className="glass-card p-6 space-y-6">
              <h2 className="text-lg font-semibold text-gray-100">
                Security Settings
              </h2>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-surface-800/50 rounded-lg border border-surface-700">
                  <div>
                    <p className="text-sm font-medium text-gray-200">
                      Two-Factor Authentication
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      Managed through your GitHub account
                    </p>
                  </div>
                  <a
                    href="https://github.com/settings/security"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-primary-400 bg-primary-500/10 rounded-lg hover:bg-primary-500/20 transition-colors"
                  >
                    Manage on GitHub <ExternalLink className="w-3 h-3" />
                  </a>
                </div>

                <div className="flex items-center justify-between p-4 bg-surface-800/50 rounded-lg border border-surface-700">
                  <div>
                    <p className="text-sm font-medium text-gray-200">
                      Active Sessions
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      Currently signed in on this device
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-teal-400">
                    <Check className="w-3.5 h-3.5" />
                    Active
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "notifications" && (
            <div className="glass-card p-6 space-y-6">
              <h2 className="text-lg font-semibold text-gray-100">
                Notification Preferences
              </h2>

              {[
                {
                  label: "Critical Vulnerabilities",
                  desc: "Alert on severity 9+ findings",
                  enabled: true,
                },
                {
                  label: "Scan Completion",
                  desc: "Notify when a security scan finishes",
                  enabled: true,
                },
                {
                  label: "Auto-Patch PRs",
                  desc: "Notify when patches are generated",
                  enabled: false,
                },
                {
                  label: "Deployment Approvals",
                  desc: "GO/NO-GO decision notifications",
                  enabled: true,
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className="flex items-center justify-between p-4 bg-surface-800/50 rounded-lg border border-surface-700"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-200">
                      {item.label}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">{item.desc}</p>
                  </div>
                  <div
                    className={`w-10 h-5 rounded-full relative cursor-pointer transition-colors ${
                      item.enabled ? "bg-primary-500" : "bg-surface-700"
                    }`}
                  >
                    <div
                      className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                        item.enabled ? "left-5" : "left-0.5"
                      }`}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === "api" && (
            <div className="glass-card p-6 space-y-6">
              <h2 className="text-lg font-semibold text-gray-100">API Keys</h2>
              <p className="text-sm text-gray-400">
                API keys allow external systems to interact with the OBSIDIAN
                Security API.
              </p>

              <div className="p-4 bg-surface-800/50 rounded-lg border border-surface-700">
                <p className="text-xs text-gray-500 mb-2">
                  Personal Access Token
                </p>
                <div className="flex gap-2">
                  <input
                    type="password"
                    value="sk-obsidian-xxxx-xxxx-xxxx"
                    className="flex-1 px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-400 font-mono"
                    readOnly
                  />
                  <button className="px-4 py-2 text-xs font-medium bg-surface-700 text-gray-300 rounded-lg hover:bg-surface-600 transition-colors">
                    Regenerate
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === "integrations" && (
            <div className="glass-card p-6 space-y-6">
              <h2 className="text-lg font-semibold text-gray-100">
                Integrations
              </h2>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-surface-800/50 rounded-lg border border-surface-700">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gray-800 rounded-lg flex items-center justify-center">
                      <svg
                        className="w-6 h-6 text-white"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                      >
                        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-200">
                        GitHub
                      </p>
                      <p className="text-xs text-gray-400">
                        Connected as {session?.user?.name || "user"}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-teal-400 bg-teal-500/10 px-3 py-1.5 rounded-full">
                    <Check className="w-3.5 h-3.5" />
                    Connected
                  </div>
                </div>

                {["Slack", "Jira", "PagerDuty"].map((service) => (
                  <div
                    key={service}
                    className="flex items-center justify-between p-4 bg-surface-800/50 rounded-lg border border-surface-700"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-surface-800 rounded-lg flex items-center justify-center">
                        <Globe className="w-5 h-5 text-gray-500" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-200">
                          {service}
                        </p>
                        <p className="text-xs text-gray-400">Not configured</p>
                      </div>
                    </div>
                    <button className="px-3 py-1.5 text-xs font-medium bg-surface-700 text-gray-300 rounded-lg hover:bg-surface-600 transition-colors">
                      Connect
                    </button>
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
