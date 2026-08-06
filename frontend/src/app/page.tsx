"use client";

import { motion } from "framer-motion";
import { Shield, Activity, GitPullRequest, GitMerge, ChevronRight, Github } from "lucide-react";
import { signIn } from "next-auth/react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-surface-950 text-gray-100 flex flex-col relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary-600/20 rounded-full blur-3xl -z-10 mix-blend-screen" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-600/20 rounded-full blur-3xl -z-10 mix-blend-screen" />

      {/* Header */}
      <header className="w-full px-8 py-6 flex items-center justify-between border-b border-surface-800/50 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <Shield className="w-8 h-8 text-primary-500" />
          <span className="font-bold text-2xl tracking-wider text-white">OBSIDIAN</span>
        </div>
        <button 
          onClick={() => signIn("github", { callbackUrl: '/dashboard' })}
          className="flex items-center gap-2 bg-surface-800 hover:bg-surface-700 border border-surface-600 px-5 py-2 rounded-lg font-medium transition-all"
        >
          <Github className="w-5 h-5" />
          <span>Login with GitHub</span>
        </button>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center text-center px-4 z-10 py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="max-w-4xl"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-400 font-medium mb-8">
            <span className="w-2 h-2 rounded-full bg-primary-500 animate-pulse" />
            The Autonomous Security Multiplex is Live
          </div>
          
          <h1 className="text-6xl md:text-7xl font-bold tracking-tight mb-8 leading-tight">
            Next-Generation <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-purple-400">Security OS</span>
          </h1>
          
          <p className="text-xl text-gray-400 mb-12 max-w-2xl mx-auto leading-relaxed">
            OBSIDIAN actively monitors your GitHub repositories, running autonomous agentic security checks on every push, and fixing vulnerabilities before they reach production.
          </p>

          <button 
            onClick={() => signIn("github", { callbackUrl: '/dashboard' })}
            className="group relative inline-flex items-center justify-center gap-3 px-8 py-4 bg-primary-600 hover:bg-primary-500 text-white font-semibold rounded-xl overflow-hidden transition-all shadow-[0_0_40px_-10px_rgba(56,189,248,0.5)]"
          >
            <Github className="w-5 h-5 relative z-10" />
            <span className="relative z-10 text-lg">Connect GitHub to Start</span>
            <ChevronRight className="w-5 h-5 relative z-10 group-hover:translate-x-1 transition-transform" />
            <div className="absolute inset-0 h-full w-full bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-shimmer" />
          </button>
        </motion.div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mt-32 w-full">
          <FeatureCard 
            icon={<Activity />}
            title="Live Security Twin"
            desc="Watch a real-time Neo4j graph representation of your repository as OBSIDIAN analyzes it."
            delay={0.2}
          />
          <FeatureCard 
            icon={<GitPullRequest />}
            title="Auto-Patching PRs"
            desc="OBSIDIAN automatically creates Pull Requests with validated fixes for high-risk vulnerabilities."
            delay={0.4}
          />
          <FeatureCard 
            icon={<GitMerge />}
            title="Zero-Intervention"
            desc="Never leave GitHub. Issues, checks, and code reviews happen entirely in the background."
            delay={0.6}
          />
        </div>
      </main>
    </div>
  );
}

function FeatureCard({ icon, title, desc, delay }: any) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="p-8 rounded-2xl bg-surface-900/50 border border-surface-800 backdrop-blur-sm text-left hover:border-primary-500/50 transition-colors group"
    >
      <div className="w-12 h-12 rounded-xl bg-surface-800 border border-surface-700 flex items-center justify-center text-primary-400 mb-6 group-hover:scale-110 transition-transform">
        {icon}
      </div>
      <h3 className="text-xl font-semibold text-white mb-3">{title}</h3>
      <p className="text-gray-400 leading-relaxed">{desc}</p>
    </motion.div>
  );
}
