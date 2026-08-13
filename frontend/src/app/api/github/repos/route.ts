import { getToken } from "next-auth/jwt";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const GITHUB_API = "https://api.github.com";
const authSecret = process.env.AUTH_SECRET || process.env.NEXTAUTH_SECRET || "";

function json(data: unknown, status = 200) {
  return NextResponse.json(data, {
    status,
    headers: {
      "Cache-Control": "private, no-store, max-age=0",
    },
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

export async function GET(req: NextRequest) {
  try {
    if (!authSecret) {
      console.error("GitHub repository route: AUTH_SECRET/NEXTAUTH_SECRET is missing");
      return json({ repos: [], error: "AUTH_CONFIG_MISSING" }, 500);
    }

    // IMPORTANT: use the same secret fallback as the NextAuth configuration.
    // Previously this route only used NEXTAUTH_SECRET, so deployments that
    // used AUTH_SECRET could see a valid login but an empty repository list.
    const token = await getToken({ req, secret: authSecret });
    const accessToken = typeof token?.accessToken === "string" ? token.accessToken : "";

    if (!accessToken) {
      return json(
        {
          repos: [],
          error: "AUTH_REQUIRED",
          message: "GitHub access is missing from the current session.",
        },
        401
      );
    }

    // GitHub returns at most 100 repositories per page. Load all available
    // pages so the dashboard does not silently stop at the first 100.
    const ghRepos: any[] = [];
    for (let page = 1; page <= 10; page += 1) {
      const response = await githubFetch(
        `/user/repos?sort=updated&direction=desc&per_page=100&page=${page}&type=all`,
        accessToken
      );

      if (response.status === 401) {
        return json(
          {
            repos: [],
            error: "GITHUB_TOKEN_INVALID",
            message: "The GitHub authorization has expired. Please sign in again.",
          },
          401
        );
      }

      if (!response.ok) {
        const body = await response.text().catch(() => "");
        console.error("GitHub API error:", response.status, body.slice(0, 500));
        return json(
          {
            repos: [],
            error: "GITHUB_API_ERROR",
            message: `GitHub returned ${response.status}.`,
          },
          502
        );
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
      // Never invent a security score. A score is shown only after OBSIDIAN
      // has actually assessed the repository.
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

    return json({ repos, count: repos.length });
  } catch (error) {
    console.error("Failed to fetch GitHub repos:", error);
    return json(
      {
        repos: [],
        error: "REPOSITORY_FETCH_FAILED",
        message: "Unable to load GitHub repositories right now.",
      },
      500
    );
  }
}
