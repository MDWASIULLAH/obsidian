import { getToken } from "next-auth/jwt";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const GITHUB_API = "https://api.github.com";
const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "https://obsidian-backend-gute.onrender.com").replace(/\/$/, "");
const authSecret = process.env.AUTH_SECRET || process.env.NEXTAUTH_SECRET || "";

function json(data: unknown, status = 200) {
  return NextResponse.json(data, {
    status,
    headers: { "Cache-Control": "private, no-store, max-age=0" },
  });
}

async function githubFetch(path: string, accessToken: string) {
  return fetch(`${GITHUB_API}${path}`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    cache: "no-store",
  });
}

async function trackedRepositoryFallback() {
  try {
    const response = await fetch(`${API_BASE}/api/v1/repositories`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return [];

    const tracked = await response.json();
    if (!Array.isArray(tracked)) return [];

    return tracked.map((repo: any) => ({
      id: String(repo.id),
      github_id: Number(repo.github_id || 0),
      full_name: repo.full_name,
      name: repo.name,
      owner: repo.owner || String(repo.full_name || "").split("/")[0],
      default_branch: repo.default_branch || "main",
      description: repo.description ?? null,
      language: repo.language ?? null,
      is_active: repo.is_active !== false,
      security_score: Number(repo.security_score || 0),
      total_scans: Number(repo.total_scans || 0),
      total_findings: Number(repo.total_findings || 0),
      total_patches: Number(repo.total_patches || 0),
      private: false,
      stargazers_count: 0,
      forks_count: 0,
      updated_at: repo.updated_at,
      created_at: repo.created_at,
      html_url: `https://github.com/${repo.full_name}`,
    }));
  } catch (error) {
    console.error("Tracked repository fallback failed:", error);
    return [];
  }
}

export async function GET(req: NextRequest) {
  try {
    if (!authSecret) {
      console.error("GitHub repository route: AUTH_SECRET/NEXTAUTH_SECRET is missing");
      return json({ repos: [], error: "AUTH_CONFIG_MISSING" }, 500);
    }

    const token = await getToken({ req, secret: authSecret });
    const accessToken = typeof token?.accessToken === "string" ? token.accessToken : "";

    if (!accessToken) {
      return json({ repos: [], error: "AUTH_REQUIRED", message: "GitHub access is missing from the current session." }, 401);
    }

    const ghRepos: any[] = [];

    for (let page = 1; page <= 10; page += 1) {
      const response = await githubFetch(
        `/user/repos?sort=updated&direction=desc&per_page=100&page=${page}&type=all`,
        accessToken,
      );

      if (response.status === 401) {
        const fallback = await trackedRepositoryFallback();
        if (fallback.length > 0) return json({ repos: fallback, count: fallback.length, source: "tracked-backend", warning: "GITHUB_TOKEN_INVALID" });
        return json({ repos: [], error: "GITHUB_TOKEN_INVALID", message: "The GitHub authorization has expired. Please sign in again." }, 401);
      }

      if (!response.ok) {
        const body = await response.text().catch(() => "");
        console.error("GitHub API error:", response.status, body.slice(0, 500));
        const fallback = await trackedRepositoryFallback();
        if (fallback.length > 0) return json({ repos: fallback, count: fallback.length, source: "tracked-backend", warning: "GITHUB_API_ERROR" });
        return json({ repos: [], error: "GITHUB_API_ERROR", message: `GitHub returned ${response.status}.` }, 502);
      }

      const pageRepos = await response.json();
      if (!Array.isArray(pageRepos)) break;
      ghRepos.push(...pageRepos);
      if (pageRepos.length < 100) break;
    }

    const repos = ghRepos.map((repo: any) => ({
      id: String(repo.id),
      github_id: repo.id,
      full_name: repo.full_name,
      name: repo.name,
      owner: repo.owner?.login || "",
      default_branch: repo.default_branch || "main",
      description: repo.description ?? null,
      language: repo.language ?? null,
      is_active: true,
      security_score: 0,
      total_scans: 0,
      total_findings: 0,
      total_patches: 0,
      private: Boolean(repo.private),
      stargazers_count: repo.stargazers_count || 0,
      forks_count: repo.forks_count || 0,
      updated_at: repo.updated_at,
      created_at: repo.created_at,
      html_url: repo.html_url,
    }));

    if (repos.length > 0) return json({ repos, count: repos.length, source: "github" });

    const fallback = await trackedRepositoryFallback();
    return json({ repos: fallback, count: fallback.length, source: fallback.length ? "tracked-backend" : "github" });
  } catch (error) {
    console.error("Failed to fetch GitHub repos:", error);
    const fallback = await trackedRepositoryFallback();
    if (fallback.length > 0) return json({ repos: fallback, count: fallback.length, source: "tracked-backend", warning: "REPOSITORY_FETCH_FAILED" });
    return json({ repos: [], error: "REPOSITORY_FETCH_FAILED", message: "Unable to load GitHub repositories right now." }, 500);
  }
}
