"""
SENTINEL AI X — GitHub Integration Client.

Full GitHub API client supporting:
  - Webhook verification (HMAC-SHA256)
  - GitHub App JWT authentication
  - GraphQL API queries
  - Repository cloning & diff extraction
  - Pull Request creation with findings
  - Check Run creation per agent
  - PR comment threading
  - Status checks
  - Comprehensive event payload parsing (22 event types)
  - Security alert fetching (Dependabot, secret scanning, code scanning)
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════
# Event Data Contract
# ═══════════════════════════════════════════════════════════════════


@dataclass
class GitHubEventData:
    """
    Normalised representation of any GitHub webhook event.

    Consumers (Digital Twin, event router, Celery tasks) use this
    instead of raw payloads, so every event type has a predictable
    shape regardless of what GitHub sends.
    """

    event_type: str
    action: str | None
    repository_full_name: str
    sender: str
    commit_sha: str | None = None
    branch: str | None = None
    pr_number: int | None = None
    changed_files: list[str] = field(default_factory=list)
    # True → triggers a full or partial security pipeline
    requires_full_pipeline: bool = False
    # True → always updates the Digital Twin graph
    requires_graph_update: bool = True
    # Subset of agents to activate (empty = use default routing)
    agent_routing_hints: list[str] = field(default_factory=list)
    # Raw sub-payload (e.g. alert object, deployment object)
    extra: dict = field(default_factory=dict)


class GitHubClient:
    """GitHub API client for SENTINEL AI X."""

    def __init__(self, user_token: str | None = None) -> None:
        settings = get_settings()
        self._token = user_token or settings.github_token
        self._api_url = settings.github_api_url
        self._graphql_url = settings.github_graphql_url
        self._webhook_secret = settings.github_webhook_secret
        self._app_id = settings.github_app_id
        self._app_private_key = settings.github_app_private_key or settings.github_private_key
        self._app_key_path = settings.github_app_private_key_path
        self._installation_id = settings.github_app_installation_id
        self._repo_cache = settings.repo_cache_dir
        self._installation_token: str | None = None
        self._installation_token_expires: float = 0.0
        self._installation_tokens: dict[int, tuple[str, float]] = {}

        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    # ═══════════════════════════════════════════════════════════
    # GitHub App JWT Authentication
    # ═══════════════════════════════════════════════════════════

    def _generate_app_jwt(self) -> str:
        """Generate a signed JWT for GitHub App authentication."""
        try:
            import jwt as pyjwt  # PyJWT
        except ImportError:
            logger.warning("PyJWT not installed; GitHub App auth unavailable")
            return ""

        key_path = Path(self._app_key_path)
        private_key = self._app_private_key.replace("\\n", "\n").strip()
        if private_key:
            pass
        elif key_path.exists():
            private_key = key_path.read_text()
        else:
            logger.warning("GitHub App private key not found", path=str(key_path))
            return ""
        now = int(time.time())
        payload = {
            "iat": now - 60,   # Allow 60s clock skew
            "exp": now + 600,  # Token valid for 10 minutes
            "iss": self._app_id,
        }
        return pyjwt.encode(payload, private_key, algorithm="RS256")

    async def _get_installation_token(self, installation_id: int | None = None) -> str:
        """
        Exchange App JWT for an installation access token.
        Tokens are cached for their ~1 hour validity window.
        """
        now = time.time()
        target_installation_id = installation_id or self._installation_id
        if target_installation_id in self._installation_tokens:
            token, expires_at = self._installation_tokens[target_installation_id]
            if now < expires_at - 60:
                return token

        jwt_token = self._generate_app_jwt()
        if not jwt_token or not target_installation_id:
            return self._token  # Fall back to PAT

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._api_url}/app/installations/{target_installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            if resp.status_code == 201:
                data = resp.json()
                expires_at = now + 3600
                self._installation_tokens[target_installation_id] = (data["token"], expires_at)
                if target_installation_id == self._installation_id:
                    self._installation_token = data["token"]
                    self._installation_token_expires = expires_at
                return data["token"]

        return self._token  # Fall back to PAT on failure

    async def _auth_headers(self) -> dict[str, str]:
        """Return the best available auth headers."""
        if self._app_id and self._installation_id:
            token = await self._get_installation_token()
        else:
            token = self._token
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _app_headers(self) -> dict[str, str]:
        """Return GitHub App JWT headers for installation management endpoints."""
        jwt_token = self._generate_app_jwt()
        if not jwt_token:
            raise RuntimeError("GitHub App credentials are not configured")
        return {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_installation(self, installation_id: int) -> dict:
        """Fetch GitHub App installation metadata."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self._api_url}/app/installations/{installation_id}",
                headers=self._app_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def list_installation_repositories(self, installation_id: int) -> list[dict]:
        """List every repository authorized for a GitHub App installation."""
        token = await self._get_installation_token(installation_id)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        repos: list[dict] = []
        page = 1
        async with httpx.AsyncClient(timeout=60) as client:
            while True:
                response = await client.get(
                    f"{self._api_url}/installation/repositories",
                    headers=headers,
                    params={"per_page": 100, "page": page},
                )
                response.raise_for_status()
                data = response.json()
                batch = data.get("repositories", [])
                repos.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
        return repos

    # ═══════════════════════════════════════════════════════════
    # Webhook Verification
    # ═══════════════════════════════════════════════════════════

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify GitHub webhook HMAC-SHA256 signature."""
        if not self._webhook_secret:
            logger.warning("Webhook secret not configured, skipping verification")
            return True

        expected = hmac.new(
            self._webhook_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        expected_sig = f"sha256={expected}"
        return hmac.compare_digest(expected_sig, signature)

    # ═══════════════════════════════════════════════════════════
    # GraphQL API
    # ═══════════════════════════════════════════════════════════

    async def graphql_query(
        self,
        query: str,
        variables: dict | None = None,
    ) -> dict:
        """Execute a GitHub GraphQL query."""
        headers = await self._auth_headers()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self._graphql_url,
                headers=headers,
                json={"query": query, "variables": variables or {}},
            )
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data:
                logger.warning("GraphQL errors", errors=data["errors"])
            return data.get("data", {})

    # ═══════════════════════════════════════════════════════════
    # Repository Operations
    # ═══════════════════════════════════════════════════════════

    async def get_repository(self, full_name: str) -> dict:
        """Get repository metadata from GitHub API."""
        headers = await self._auth_headers()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._api_url}/repos/{full_name}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_repository_tree(
        self,
        full_name: str,
        sha: str = "HEAD",
        recursive: bool = True,
    ) -> list[dict]:
        """Get the full file tree for a repository at a given ref."""
        headers = await self._auth_headers()
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(
                f"{self._api_url}/repos/{full_name}/git/trees/{sha}",
                headers=headers,
                params={"recursive": "1" if recursive else "0"},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("tree", [])

    async def get_file_content(
        self,
        full_name: str,
        path: str,
        ref: str = "HEAD",
    ) -> str | None:
        """Fetch raw file content from GitHub. Returns None if not accessible."""
        import base64
        headers = await self._auth_headers()
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(
                    f"{self._api_url}/repos/{full_name}/contents/{path}",
                    headers=headers,
                    params={"ref": ref},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("encoding") == "base64":
                        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            except Exception as e:
                logger.debug("Could not fetch file", file=path, error=str(e))
        return None

    async def clone_or_pull(self, full_name: str, branch: str = "main") -> Path:
        """Clone or update a repository locally."""
        from git import Repo as GitRepo
        token = await self._get_installation_token() if self._app_id else self._token
        repo_dir = self._repo_cache / full_name.replace("/", "_")
        repo_dir.mkdir(parents=True, exist_ok=True)
        clone_url = f"https://x-access-token:{token}@github.com/{full_name}.git"

        if (repo_dir / ".git").exists():
            repo = GitRepo(repo_dir)
            origin = repo.remotes.origin
            origin.fetch()
            repo.git.checkout(branch)
            repo.git.pull()
            logger.info("Repository updated", repo=full_name, branch=branch)
        else:
            GitRepo.clone_from(clone_url, repo_dir, branch=branch)
            logger.info("Repository cloned", repo=full_name, branch=branch)

        return repo_dir

    async def get_commit_diff(
        self,
        full_name: str,
        commit_sha: str,
    ) -> dict[str, Any]:
        """Get diff and changed files for a specific commit."""
        import base64
        headers = await self._auth_headers()
        async with httpx.AsyncClient(timeout=60) as client:
            diff_resp = await client.get(
                f"{self._api_url}/repos/{full_name}/commits/{commit_sha}",
                headers={**headers, "Accept": "application/vnd.github.diff"},
            )
            diff_resp.raise_for_status()
            diff_content = diff_resp.text

            meta_resp = await client.get(
                f"{self._api_url}/repos/{full_name}/commits/{commit_sha}",
                headers=headers,
            )
            meta_resp.raise_for_status()
            commit_data = meta_resp.json()
            changed_files = [f["filename"] for f in commit_data.get("files", [])]

            file_contents: dict[str, str] = {}
            for filename in changed_files[:30]:
                try:
                    resp = await client.get(
                        f"{self._api_url}/repos/{full_name}/contents/{filename}",
                        headers=headers,
                        params={"ref": commit_sha},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("encoding") == "base64":
                            file_contents[filename] = base64.b64decode(
                                data["content"]
                            ).decode("utf-8", errors="replace")
                except Exception as e:
                    logger.debug("Could not fetch file", file=filename, error=str(e))

            return {
                "diff": diff_content,
                "changed_files": changed_files,
                "file_contents": file_contents,
            }

    # ═══════════════════════════════════════════════════════════
    # Event Payload Parsing
    # ═══════════════════════════════════════════════════════════

    # Maps event types → (requires_full_pipeline, agent_routing_hints)
    _EVENT_ROUTING: dict[str, tuple[bool, list[str]]] = {
        "push":                       (True,  []),
        "pull_request":               (True,  []),
        "pull_request_review":        (False, []),
        "issues":                     (False, []),
        "issue_comment":              (False, []),
        "release":                    (True,  ["compliance_auditor", "deployment_approval"]),
        "create":                     (False, []),
        "delete":                     (False, []),
        "branch_protection_rule":     (False, ["compliance_auditor"]),
        "deployment":                 (True,  ["infra_security", "container_security"]),
        "deployment_status":          (False, []),
        "workflow_run":               (False, ["infra_security"]),
        "workflow_job":               (False, ["infra_security"]),
        "check_run":                  (False, []),
        "check_suite":                (False, []),
        "security_advisory":          (True,  ["dependency_intel", "threat_modeler"]),
        "secret_scanning_alert":      (True,  ["secrets_detection"]),
        "code_scanning_alert":        (True,  ["code_intelligence"]),
        "dependabot_alert":           (True,  ["dependency_intel"]),
        "repository":                 (False, []),
        "member":                     (False, []),
        "discussion":                 (False, []),
        "discussion_comment":         (False, []),
    }

    def parse_event_payload(
        self,
        event_type: str,
        payload: dict,
    ) -> GitHubEventData:
        """
        Normalise any GitHub webhook payload into a GitHubEventData.

        Extracts the minimal fields every consumer needs regardless
        of which event type was fired.
        """
        repo = payload.get("repository", {})
        full_name = repo.get("full_name", "")
        sender = payload.get("sender", {}).get("login", "github")
        action = payload.get("action")

        requires_pipeline, hints = self._EVENT_ROUTING.get(
            event_type, (False, [])
        )

        commit_sha: str | None = None
        branch: str | None = None
        pr_number: int | None = None
        changed_files: list[str] = []
        extra: dict = {}

        if event_type == "push":
            ref = payload.get("ref", "")
            branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref
            commit_sha = payload.get("after") or payload.get("head_commit", {}).get("id")
            commits = payload.get("commits", [])
            seen: set[str] = set()
            for c in commits:
                for f in c.get("added", []) + c.get("modified", []) + c.get("removed", []):
                    if f not in seen:
                        changed_files.append(f)
                        seen.add(f)

        elif event_type in ("pull_request", "pull_request_review"):
            pr = payload.get("pull_request", {})
            pr_number = pr.get("number")
            commit_sha = pr.get("head", {}).get("sha")
            branch = pr.get("head", {}).get("ref")

        elif event_type in ("create", "delete"):
            ref_type = payload.get("ref_type", "")
            ref = payload.get("ref", "")
            if ref_type == "branch":
                branch = ref
            extra = {"ref_type": ref_type, "ref": ref}

        elif event_type == "deployment":
            d = payload.get("deployment", {})
            commit_sha = d.get("sha")
            branch = d.get("ref")
            extra = {"environment": d.get("environment"), "task": d.get("task")}

        elif event_type == "workflow_run":
            wf = payload.get("workflow_run", {})
            commit_sha = wf.get("head_sha")
            branch = wf.get("head_branch")
            extra = {
                "workflow_name": wf.get("name"),
                "conclusion": wf.get("conclusion"),
                "status": wf.get("status"),
            }

        elif event_type in ("security_advisory", "dependabot_alert",
                            "secret_scanning_alert", "code_scanning_alert"):
            alert_key = {
                "security_advisory": "security_advisory",
                "dependabot_alert": "alert",
                "secret_scanning_alert": "alert",
                "code_scanning_alert": "alert",
            }[event_type]
            extra = payload.get(alert_key, {})

        elif event_type == "release":
            rel = payload.get("release", {})
            commit_sha = rel.get("target_commitish")
            extra = {
                "tag_name": rel.get("tag_name"),
                "prerelease": rel.get("prerelease"),
            }

        elif event_type == "branch_protection_rule":
            extra = payload.get("rule", {})
            branch = payload.get("rule", {}).get("name")

        return GitHubEventData(
            event_type=event_type,
            action=action,
            repository_full_name=full_name,
            sender=sender,
            commit_sha=commit_sha,
            branch=branch,
            pr_number=pr_number,
            changed_files=changed_files,
            requires_full_pipeline=requires_pipeline,
            requires_graph_update=True,
            agent_routing_hints=hints,
            extra=extra,
        )

    # ═══════════════════════════════════════════════════════════
    # Security Alerts
    # ═══════════════════════════════════════════════════════════

    async def get_security_alerts(self, full_name: str) -> dict[str, list]:
        """Fetch all active security alerts for a repository."""
        headers = await self._auth_headers()
        results: dict[str, list] = {
            "dependabot": [],
            "secret_scanning": [],
            "code_scanning": [],
        }
        async with httpx.AsyncClient(timeout=30) as client:
            for key, path in [
                ("dependabot", f"/repos/{full_name}/dependabot/alerts"),
                ("secret_scanning", f"/repos/{full_name}/secret-scanning/alerts"),
                ("code_scanning", f"/repos/{full_name}/code-scanning/alerts"),
            ]:
                try:
                    resp = await client.get(
                        f"{self._api_url}{path}",
                        headers=headers,
                        params={"state": "open", "per_page": 100},
                    )
                    if resp.status_code == 200:
                        results[key] = resp.json()
                except Exception as e:
                    logger.debug(f"Could not fetch {key} alerts", error=str(e))
        return results

    async def get_branch_protection(self, full_name: str, branch: str) -> dict:
        """Get branch protection rules."""
        headers = await self._auth_headers()
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(
                    f"{self._api_url}/repos/{full_name}/branches/{branch}/protection",
                    headers=headers,
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception as e:
                logger.debug("Could not fetch branch protection", error=str(e))
        return {}

    # ═══════════════════════════════════════════════════════════
    # Pull Request Operations
    # ═══════════════════════════════════════════════════════════

    async def create_pull_request(
        self,
        full_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> dict:
        """Create a pull request with security findings."""
        headers = await self._auth_headers()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._api_url}/repos/{full_name}/pulls",
                headers=headers,
                json={
                    "title": title,
                    "body": body,
                    "head": head_branch,
                    "base": base_branch,
                },
            )
            response.raise_for_status()
            pr_data = response.json()
            logger.info(
                "Pull request created",
                repo=full_name,
                pr_number=pr_data["number"],
                url=pr_data["html_url"],
            )
            return pr_data

    async def create_pr_comment(
        self,
        full_name: str,
        pr_number: int,
        body: str,
    ) -> dict:
        """Add a comment to a pull request."""
        headers = await self._auth_headers()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._api_url}/repos/{full_name}/issues/{pr_number}/comments",
                headers=headers,
                json={"body": body},
            )
            response.raise_for_status()
            return response.json()

    async def create_review_comment(
        self,
        full_name: str,
        pr_number: int,
        commit_sha: str,
        file_path: str,
        line: int,
        body: str,
    ) -> dict:
        """Create an inline review comment on a specific line."""
        headers = await self._auth_headers()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._api_url}/repos/{full_name}/pulls/{pr_number}/comments",
                headers=headers,
                json={
                    "body": body,
                    "commit_id": commit_sha,
                    "path": file_path,
                    "line": line,
                    "side": "RIGHT",
                },
            )
            response.raise_for_status()
            return response.json()

    # ═══════════════════════════════════════════════════════════
    # Issues & Labels
    # ═══════════════════════════════════════════════════════════

    async def create_issue(
        self,
        full_name: str,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> dict:
        """Create a GitHub issue."""
        headers = await self._auth_headers()
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._api_url}/repos/{full_name}/issues",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def add_labels(
        self,
        full_name: str,
        issue_or_pr_number: int,
        labels: list[str],
    ) -> dict | list:
        """Add labels to an issue or pull request."""
        headers = await self._auth_headers()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._api_url}/repos/{full_name}/issues/{issue_or_pr_number}/labels",
                headers=headers,
                json={"labels": labels},
            )
            response.raise_for_status()
            return response.json()

    # ═══════════════════════════════════════════════════════════
    # Check Runs
    # ═══════════════════════════════════════════════════════════

    async def create_check_run(
        self,
        full_name: str,
        name: str,
        head_sha: str,
        status: str = "in_progress",
        conclusion: str | None = None,
        output: dict | None = None,
    ) -> dict:
        """Create or update a check run for an agent."""
        headers = await self._auth_headers()
        async with httpx.AsyncClient() as client:
            payload: dict[str, Any] = {
                "name": f"SENTINEL AI X: {name}",
                "head_sha": head_sha,
                "status": status,
            }
            if conclusion:
                payload["conclusion"] = conclusion
            if output:
                payload["output"] = output

            response = await client.post(
                f"{self._api_url}/repos/{full_name}/check-runs",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    # ═══════════════════════════════════════════════════════════
    # Status Checks
    # ═══════════════════════════════════════════════════════════

    async def create_commit_status(
        self,
        full_name: str,
        sha: str,
        state: str,
        description: str,
        context: str = "SENTINEL AI X",
        target_url: str | None = None,
    ) -> dict:
        """Set a commit status check."""
        headers = await self._auth_headers()
        async with httpx.AsyncClient() as client:
            payload: dict[str, Any] = {
                "state": state,
                "description": description[:140],
                "context": context,
            }
            if target_url:
                payload["target_url"] = target_url

            response = await client.post(
                f"{self._api_url}/repos/{full_name}/statuses/{sha}",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()


# ── Singleton ──────────────────────────────────────────────────────

_client: GitHubClient | None = None


def get_github_client() -> GitHubClient:
    """Get or create the singleton GitHubClient."""
    global _client
    if _client is None:
        _client = GitHubClient()
    return _client


    # ═══════════════════════════════════════════════════════════
    # Webhook Verification
    # ═══════════════════════════════════════════════════════════

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify GitHub webhook HMAC-SHA256 signature."""
        if not self._webhook_secret:
            logger.warning("Webhook secret not configured, skipping verification")
            return True

        expected = hmac.new(
            self._webhook_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        expected_sig = f"sha256={expected}"
        return hmac.compare_digest(expected_sig, signature)

    # ═══════════════════════════════════════════════════════════
    # Repository Operations
    # ═══════════════════════════════════════════════════════════

    async def get_repository(self, full_name: str) -> dict:
        """Get repository metadata from GitHub API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._api_url}/repos/{full_name}",
                headers=self._headers,
            )
            response.raise_for_status()
            return response.json()

    async def clone_or_pull(self, full_name: str, branch: str = "main") -> Path:
        """Clone or update a repository locally."""
        repo_dir = self._repo_cache / full_name.replace("/", "_")
        repo_dir.mkdir(parents=True, exist_ok=True)

        clone_url = f"https://x-access-token:{self._token}@github.com/{full_name}.git"

        if (repo_dir / ".git").exists():
            repo = GitRepo(repo_dir)
            origin = repo.remotes.origin
            origin.fetch()
            repo.git.checkout(branch)
            repo.git.pull()
            logger.info("Repository updated", repo=full_name, branch=branch)
        else:
            repo = GitRepo.clone_from(clone_url, repo_dir, branch=branch)
            logger.info("Repository cloned", repo=full_name, branch=branch)

        return repo_dir

    async def get_commit_diff(
        self,
        full_name: str,
        commit_sha: str,
    ) -> dict[str, Any]:
        """
        Get diff and changed files for a specific commit.

        Returns:
            {
                "diff": "unified diff string",
                "changed_files": ["file1.py", "file2.js"],
                "file_contents": {"file1.py": "content..."}
            }
        """
        async with httpx.AsyncClient() as client:
            # Get commit with diff
            response = await client.get(
                f"{self._api_url}/repos/{full_name}/commits/{commit_sha}",
                headers={
                    **self._headers,
                    "Accept": "application/vnd.github.diff",
                },
            )
            response.raise_for_status()
            diff_content = response.text

            # Get file list
            response = await client.get(
                f"{self._api_url}/repos/{full_name}/commits/{commit_sha}",
                headers=self._headers,
            )
            response.raise_for_status()
            commit_data = response.json()

            changed_files = [
                f["filename"] for f in commit_data.get("files", [])
            ]

            # Get file contents for changed files
            file_contents = {}
            for filename in changed_files[:30]:  # Limit to 30 files
                try:
                    resp = await client.get(
                        f"{self._api_url}/repos/{full_name}/contents/{filename}",
                        headers=self._headers,
                        params={"ref": commit_sha},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("encoding") == "base64":
                            import base64
                            file_contents[filename] = base64.b64decode(
                                data["content"]
                            ).decode("utf-8", errors="replace")
                except Exception as e:
                    logger.debug("Could not fetch file", file=filename, error=str(e))

            return {
                "diff": diff_content,
                "changed_files": changed_files,
                "file_contents": file_contents,
            }

    # ═══════════════════════════════════════════════════════════
    # Pull Request Operations
    # ═══════════════════════════════════════════════════════════

    async def create_pull_request(
        self,
        full_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> dict:
        """Create a pull request with security findings."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._api_url}/repos/{full_name}/pulls",
                headers=self._headers,
                json={
                    "title": title,
                    "body": body,
                    "head": head_branch,
                    "base": base_branch,
                },
            )
            response.raise_for_status()
            pr_data = response.json()

            logger.info(
                "Pull request created",
                repo=full_name,
                pr_number=pr_data["number"],
                url=pr_data["html_url"],
            )
            return pr_data

    async def create_pr_comment(
        self,
        full_name: str,
        pr_number: int,
        body: str,
    ) -> dict:
        """Add a comment to a pull request."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._api_url}/repos/{full_name}/issues/{pr_number}/comments",
                headers=self._headers,
                json={"body": body},
            )
            response.raise_for_status()
            return response.json()

    async def create_review_comment(
        self,
        full_name: str,
        pr_number: int,
        commit_sha: str,
        file_path: str,
        line: int,
        body: str,
    ) -> dict:
        """Create an inline review comment on a specific line."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._api_url}/repos/{full_name}/pulls/{pr_number}/comments",
                headers=self._headers,
                json={
                    "body": body,
                    "commit_id": commit_sha,
                    "path": file_path,
                    "line": line,
                    "side": "RIGHT",
                },
            )
            response.raise_for_status()
            return response.json()

    # ═══════════════════════════════════════════════════════════
    # Check Runs (Status Indicators)
    # ═══════════════════════════════════════════════════════════

    async def create_check_run(
        self,
        full_name: str,
        name: str,
        head_sha: str,
        status: str = "in_progress",
        conclusion: str | None = None,
        output: dict | None = None,
    ) -> dict:
        """Create or update a check run for an agent."""
        async with httpx.AsyncClient() as client:
            payload: dict[str, Any] = {
                "name": f"SENTINEL AI X: {name}",
                "head_sha": head_sha,
                "status": status,
            }
            if conclusion:
                payload["conclusion"] = conclusion
            if output:
                payload["output"] = output

            response = await client.post(
                f"{self._api_url}/repos/{full_name}/check-runs",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    # ═══════════════════════════════════════════════════════════
    # Status Checks
    # ═══════════════════════════════════════════════════════════

    async def create_commit_status(
        self,
        full_name: str,
        sha: str,
        state: str,  # error, failure, pending, success
        description: str,
        context: str = "SENTINEL AI X",
        target_url: str | None = None,
    ) -> dict:
        """Set a commit status check."""
        async with httpx.AsyncClient() as client:
            payload: dict[str, Any] = {
                "state": state,
                "description": description[:140],
                "context": context,
            }
            if target_url:
                payload["target_url"] = target_url

            response = await client.post(
                f"{self._api_url}/repos/{full_name}/statuses/{sha}",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()


# ── Singleton ──────────────────────────────────────────────────────

_client: GitHubClient | None = None


def get_github_client() -> GitHubClient:
    """Get or create the singleton GitHubClient."""
    global _client
    if _client is None:
        _client = GitHubClient()
    return _client
