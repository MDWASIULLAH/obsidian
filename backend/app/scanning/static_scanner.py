"""Deterministic repository security checks used alongside AI agents."""

from __future__ import annotations

import re
from typing import Any

SECRET_PATTERNS = [
    ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("Private Key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    (
        "Generic Secret Assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret[_-]?key|password|passwd|token)\b\s*[:=]\s*[\"'][^\"'\n]{8,}[\"']"
        ),
    ),
]

CODE_RULES = [
    (
        "SQL Injection",
        "CWE-89",
        "critical",
        re.compile(
            r"(?i)(?:execute|executemany|cursor\.execute)\s*\(\s*(?:f[\"']|[\"'].*(?:SELECT|INSERT|UPDATE|DELETE).*\{)"
        ),
        "Use parameterized queries instead of string interpolation.",
    ),
    (
        "Command Injection",
        "CWE-78",
        "high",
        re.compile(
            r"(?i)\b(?:os\.system|os\.popen)\s*\(|subprocess\.(?:run|Popen|call|check_output)\s*\([^)]*shell\s*=\s*True"
        ),
        "Avoid shell execution with untrusted input; use argument arrays and strict validation.",
    ),
    (
        "Dangerous eval",
        "CWE-95",
        "high",
        re.compile(r"\b(?:eval|exec)\s*\("),
        "Avoid eval/exec on untrusted or dynamically constructed input.",
    ),
    (
        "Unsafe YAML Load",
        "CWE-502",
        "high",
        re.compile(r"yaml\.load\s*\("),
        "Use yaml.safe_load for untrusted YAML.",
    ),
    (
        "Insecure TLS Verification",
        "CWE-295",
        "high",
        re.compile(r"(?i)(?:verify\s*=\s*False|ssl\._create_unverified_context)"),
        "Keep TLS certificate verification enabled.",
    ),
    (
        "Weak Hash Algorithm",
        "CWE-328",
        "medium",
        re.compile(r"\bhashlib\.(?:md5|sha1)\s*\("),
        "Use a modern collision-resistant hash such as SHA-256 when appropriate.",
    ),
    (
        "Hardcoded Debug Mode",
        "CWE-489",
        "medium",
        re.compile(r"(?i)(?:debug\s*=\s*True|DEBUG\s*=\s*True)"),
        "Disable debug mode in production.",
    ),
]


def scan_repository_files(file_contents: dict[str, str]) -> list[dict[str, Any]]:
    """Run deterministic checks against the real repository contents."""
    findings: list[dict[str, Any]] = []

    for path, content in file_contents.items():
        if not content:
            continue
        lines = content.splitlines()

        for title, pattern in SECRET_PATTERNS:
            match = pattern.search(content)
            if match:
                line = content[: match.start()].count("\n") + 1
                findings.append(
                    {
                        "title": title,
                        "description": f"Potential {title.lower()} detected in source code. The scanner does not store the matched secret value.",
                        "severity": "critical",
                        "category": "secret",
                        "confidence": 0.98,
                        "file_path": path,
                        "line_start": line,
                        "code_snippet": "[REDACTED]",
                        "recommendation": "Move credentials to a secrets manager/environment variable and rotate any exposed credential.",
                        "agent_name": "static_scanner",
                    }
                )

        for title, cwe, severity, pattern, recommendation in CODE_RULES:
            match = pattern.search(content)
            if match:
                line = content[: match.start()].count("\n") + 1
                findings.append(
                    {
                        "title": title,
                        "description": f"Potential {title.lower()} pattern detected by deterministic static analysis.",
                        "severity": severity,
                        "category": "static_analysis",
                        "confidence": 0.90,
                        "file_path": path,
                        "line_start": line,
                        "cwe_id": cwe,
                        "code_snippet": lines[line - 1][:500] if 0 < line <= len(lines) else None,
                        "recommendation": recommendation,
                        "agent_name": "static_scanner",
                    }
                )

    unique: dict[tuple[str | None, str], dict[str, Any]] = {}
    for finding in findings:
        unique[(finding.get("file_path"), finding.get("title", ""))] = finding
    return list(unique.values())
