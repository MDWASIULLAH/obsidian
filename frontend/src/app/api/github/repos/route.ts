import { getToken } from "next-auth/jwt";
import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  try {
    // Get the JWT token which contains the GitHub access token
    const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });

    if (!token?.accessToken) {
      return NextResponse.json({ repos: [] });
    }

    // Fetch repos from GitHub API
    const response = await fetch(
      "https://api.github.com/user/repos?sort=updated&per_page=100&type=all",
      {
        headers: {
          Authorization: `Bearer ${token.accessToken}`,
          Accept: "application/vnd.github+json",
        },
      }
    );

    if (!response.ok) {
      console.error("GitHub API error:", response.status);
      return NextResponse.json({ repos: [] });
    }

    const ghRepos = await response.json();

    // Map GitHub repos to our format
    const repos = ghRepos.map((repo: any) => ({
      id: String(repo.id),
      github_id: repo.id,
      full_name: repo.full_name,
      name: repo.name,
      owner: repo.owner?.login || "",
      default_branch: repo.default_branch || "main",
      description: repo.description,
      language: repo.language,
      is_active: true,
      security_score: Math.floor(Math.random() * 30) + 70, // placeholder
      total_scans: 0,
      total_findings: 0,
      total_patches: 0,
      private: repo.private,
      stargazers_count: repo.stargazers_count || 0,
      forks_count: repo.forks_count || 0,
      updated_at: repo.updated_at,
      created_at: repo.created_at,
      html_url: repo.html_url,
    }));

    return NextResponse.json({ repos });
  } catch (error) {
    console.error("Failed to fetch GitHub repos:", error);
    return NextResponse.json({ repos: [] });
  }
}
