"""
OBSIDIAN — Security Knowledge Base Loader.

Loads OWASP Top 10, MITRE ATT&CK, CWE, CAPEC, and secure
coding guidelines into Qdrant for RAG retrieval.

Each entry is chunked, embedded, and stored with rich metadata
so agents can cite specific sources in their findings.
"""

from __future__ import annotations

import structlog

from app.knowledge.rag import RAGService

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════
# OWASP Top 10 (2021)
# ═══════════════════════════════════════════════════════════════════

OWASP_TOP_10 = [
    {
        "text": "A01:2021 Broken Access Control - Access control enforces policy such that users cannot act outside of their intended permissions. Failures typically lead to unauthorized information disclosure, modification, or destruction of all data or performing a business function outside the user's limits. Common vulnerabilities include: violation of least privilege, bypassing access control checks by modifying the URL, API request, or internal state; Permitting viewing or editing someone else's account by providing its unique identifier (IDOR); accessing APIs with missing access controls for POST, PUT, and DELETE; elevation of privilege.",
        "metadata": {"title": "A01:2021 Broken Access Control", "category": "owasp_top10", "severity": "critical", "cwe_id": "CWE-284", "url": "https://owasp.org/Top10/A01_2021-Broken_Access_Control/"},
    },
    {
        "text": "A02:2021 Cryptographic Failures - Failures related to cryptography which often lead to sensitive data exposure. Determining the protection needs of data in transit and at rest. Are any old or weak cryptographic algorithms or protocols used? Are weak crypto keys generated, reused, or is proper key management missing? Is encryption not enforced through directives or headers? Is the received server certificate and trust chain properly validated?",
        "metadata": {"title": "A02:2021 Cryptographic Failures", "category": "owasp_top10", "severity": "critical", "cwe_id": "CWE-327", "url": "https://owasp.org/Top10/A02_2021-Cryptographic_Failures/"},
    },
    {
        "text": "A03:2021 Injection - An application is vulnerable to injection when: user-supplied data is not validated, filtered, or sanitized; dynamic queries or non-parameterized calls without context-aware escaping are used; hostile data is used within ORM search parameters to extract additional records; hostile data is directly used or concatenated. Common injections: SQL, NoSQL, OS command, LDAP, ORM, Expression Language, OGNL injection. Source code review and automated SAST/DAST testing recommended.",
        "metadata": {"title": "A03:2021 Injection", "category": "owasp_top10", "severity": "critical", "cwe_id": "CWE-79", "url": "https://owasp.org/Top10/A03_2021-Injection/"},
    },
    {
        "text": "A04:2021 Insecure Design - Insecure design is a broad category representing different weaknesses, expressed as missing or ineffective control design. Insecure design is not the source for all other Top 10 risk categories. There is a difference between insecure design and insecure implementation. Secure design can still have implementation defects. An insecure design cannot be fixed by a perfect implementation. Use threat modeling, secure design patterns, and reference architectures.",
        "metadata": {"title": "A04:2021 Insecure Design", "category": "owasp_top10", "severity": "high", "cwe_id": "CWE-502", "url": "https://owasp.org/Top10/A04_2021-Insecure_Design/"},
    },
    {
        "text": "A05:2021 Security Misconfiguration - The application might be vulnerable if: missing appropriate security hardening, improperly configured permissions on cloud services, unnecessary features enabled, default accounts unchanged, error handling reveals overly informative messages, security settings not set to secure values, server does not send security headers, software is out of date.",
        "metadata": {"title": "A05:2021 Security Misconfiguration", "category": "owasp_top10", "severity": "high", "cwe_id": "CWE-16", "url": "https://owasp.org/Top10/A05_2021-Security_Misconfiguration/"},
    },
    {
        "text": "A06:2021 Vulnerable and Outdated Components - You are likely vulnerable if: you do not know the versions of all components you use, the software is out of support or unpatched, you do not scan for vulnerabilities regularly, you do not fix or upgrade the platform, frameworks, and dependencies in a timely fashion, developers do not test compatibility of updated libraries, you do not secure component configurations.",
        "metadata": {"title": "A06:2021 Vulnerable Components", "category": "owasp_top10", "severity": "high", "cwe_id": "CWE-1104", "url": "https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/"},
    },
    {
        "text": "A07:2021 Identification and Authentication Failures - Confirmation of the user's identity, authentication, and session management is critical. The application may have authentication weaknesses if: permits automated attacks like credential stuffing, permits brute force, permits default/weak/well-known passwords, uses weak credential recovery processes, uses plain text/encrypted/weakly hashed password stores, has missing or ineffective MFA, exposes session identifier in URL.",
        "metadata": {"title": "A07:2021 Auth Failures", "category": "owasp_top10", "severity": "critical", "cwe_id": "CWE-287", "url": "https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/"},
    },
    {
        "text": "A08:2021 Software and Data Integrity Failures - Software and data integrity failures relate to code and infrastructure that does not protect against integrity violations. Examples: application relying on plugins/libraries/modules from untrusted sources, repositories, or CDNs. An insecure CI/CD pipeline can introduce the potential for unauthorized access, malicious code, or system compromise. Auto-update functionality without sufficient integrity verification.",
        "metadata": {"title": "A08:2021 Integrity Failures", "category": "owasp_top10", "severity": "high", "cwe_id": "CWE-829", "url": "https://owasp.org/Top10/A08_2021-Software_and_Data_Integrity_Failures/"},
    },
    {
        "text": "A09:2021 Security Logging and Monitoring Failures - Without logging and monitoring, breaches cannot be detected. Insufficient logging, detection, monitoring, and active response occurs when: auditable events such as logins, failed logins, and high-value transactions are not logged; warnings and errors generate no, inadequate, or unclear log messages; logs only stored locally; appropriate alerting thresholds and response escalation processes are not in place.",
        "metadata": {"title": "A09:2021 Logging Failures", "category": "owasp_top10", "severity": "medium", "cwe_id": "CWE-778", "url": "https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/"},
    },
    {
        "text": "A10:2021 Server-Side Request Forgery (SSRF) - SSRF flaws occur whenever a web application fetches a remote resource without validating the user-supplied URL. It allows an attacker to coerce the application to send a crafted request to an unexpected destination, even when protected by a firewall, VPN, or another type of network ACL. Fetching a URL can be a common scenario, adopting SSRF protections is critical.",
        "metadata": {"title": "A10:2021 SSRF", "category": "owasp_top10", "severity": "high", "cwe_id": "CWE-918", "url": "https://owasp.org/Top10/A10_2021-Server-Side_Request_Forgery/"},
    },
]


# ═══════════════════════════════════════════════════════════════════
# CWE Categories
# ═══════════════════════════════════════════════════════════════════

CWE_ENTRIES = [
    {"text": "CWE-79: Improper Neutralization of Input During Web Page Generation (XSS) - The software does not neutralize or incorrectly neutralizes user-controllable input before it is placed in output that is used as a web page that is served to other users. Mitigations: Use context-aware output encoding/escaping, validate all input, use Content Security Policy headers.", "metadata": {"title": "CWE-79 XSS", "category": "cwe", "cwe_id": "CWE-79", "severity": "high"}},
    {"text": "CWE-89: Improper Neutralization of Special Elements used in an SQL Command (SQL Injection) - The software constructs all or part of an SQL command using externally-influenced input but does not neutralize special elements that could modify the intended SQL command. Mitigations: Use parameterized queries/prepared statements, whitelist input validation, escape all user-supplied input.", "metadata": {"title": "CWE-89 SQL Injection", "category": "cwe", "cwe_id": "CWE-89", "severity": "critical"}},
    {"text": "CWE-78: Improper Neutralization of Special Elements used in an OS Command (OS Command Injection) - The software constructs all or part of an OS command using externally-influenced input but does not neutralize special elements that could modify the intended OS command. Mitigations: Use library functions rather than external processes, validate input, use allowlists.", "metadata": {"title": "CWE-78 OS Command Injection", "category": "cwe", "cwe_id": "CWE-78", "severity": "critical"}},
    {"text": "CWE-287: Improper Authentication - When an actor claims to have a given identity, the software does not prove or insufficiently proves that the claim is correct. Mitigations: Use proven authentication frameworks, enforce strong password policies, implement MFA, use secure session management.", "metadata": {"title": "CWE-287 Improper Auth", "category": "cwe", "cwe_id": "CWE-287", "severity": "critical"}},
    {"text": "CWE-862: Missing Authorization - The software does not perform an authorization check when an actor attempts to access a resource or perform an action. Mitigations: Enforce authorization checks on every request, implement role-based access control, follow principle of least privilege.", "metadata": {"title": "CWE-862 Missing AuthZ", "category": "cwe", "cwe_id": "CWE-862", "severity": "critical"}},
    {"text": "CWE-200: Exposure of Sensitive Information to an Unauthorized Actor - The software exposes sensitive information to an actor that is not explicitly authorized to have access to that information. Mitigations: Apply access controls, sanitize error messages, avoid verbose debug output in production.", "metadata": {"title": "CWE-200 Info Exposure", "category": "cwe", "cwe_id": "CWE-200", "severity": "high"}},
    {"text": "CWE-352: Cross-Site Request Forgery (CSRF) - The web application does not sufficiently verify whether a well-formed, valid, consistent request was intentionally provided by the user who submitted the request. Mitigations: Use anti-CSRF tokens, check the Referer header, use SameSite cookie attribute.", "metadata": {"title": "CWE-352 CSRF", "category": "cwe", "cwe_id": "CWE-352", "severity": "high"}},
    {"text": "CWE-502: Deserialization of Untrusted Data - The application deserializes untrusted data without sufficiently verifying that the resulting data will be valid. Mitigations: Avoid deserialization of untrusted data, use JSON instead of native serialization, implement integrity checks.", "metadata": {"title": "CWE-502 Insecure Deserialization", "category": "cwe", "cwe_id": "CWE-502", "severity": "critical"}},
]


# ═══════════════════════════════════════════════════════════════════
# MITRE ATT&CK Techniques
# ═══════════════════════════════════════════════════════════════════

MITRE_ENTRIES = [
    {"text": "T1190 - Exploit Public-Facing Application: Adversaries may attempt to exploit a weakness in an Internet-facing host or system to initially access a network. The weakness in the system can be a software bug, a temporary glitch, or a misconfiguration. Exploited applications are often websites/web servers, but can also include databases, standard services, and network device administration protocols.", "metadata": {"title": "T1190 Exploit Public App", "category": "mitre_attack", "technique_id": "T1190"}},
    {"text": "T1059 - Command and Scripting Interpreter: Adversaries may abuse command and script interpreters to execute commands, scripts, or binaries. These interfaces and languages provide ways of interacting with computer systems and are a common feature across many platforms. Most systems come with some built-in command-line interface and scripting capabilities.", "metadata": {"title": "T1059 Command Interpreter", "category": "mitre_attack", "technique_id": "T1059"}},
    {"text": "T1078 - Valid Accounts: Adversaries may obtain and abuse credentials of existing accounts as a means of gaining Initial Access, Persistence, Privilege Escalation, or Defense Evasion. Compromised credentials may be used to bypass access controls placed on various resources on systems within the network.", "metadata": {"title": "T1078 Valid Accounts", "category": "mitre_attack", "technique_id": "T1078"}},
    {"text": "T1055 - Process Injection: Adversaries may inject code into processes in order to evade process-based defenses as well as possibly elevate privileges. Process injection is a method of executing arbitrary code in the address space of a separate live process. Running code in the context of another process may allow access to the process's memory, system/network resources, and possibly elevated privileges.", "metadata": {"title": "T1055 Process Injection", "category": "mitre_attack", "technique_id": "T1055"}},
    {"text": "T1027 - Obfuscated Files or Information: Adversaries may attempt to make an executable or file difficult to discover or analyze by encrypting, encoding, or otherwise obfuscating its contents on the system or in transit. This is common behavior that can be used across different platforms to evade defenses.", "metadata": {"title": "T1027 Obfuscation", "category": "mitre_attack", "technique_id": "T1027"}},
]


# ═══════════════════════════════════════════════════════════════════
# Loader
# ═══════════════════════════════════════════════════════════════════


async def load_security_knowledge_base(rag_service: RAGService) -> dict[str, int]:
    """
    Load all security knowledge into Qdrant.

    Returns counts of ingested documents per collection.
    """
    logger.info("📚 Loading security knowledge base into Qdrant")

    counts = {}

    # OWASP Top 10
    counts["owasp_top10"] = await rag_service.ingest_documents(
        "owasp_top10", OWASP_TOP_10
    )

    # CWE
    counts["cwe"] = await rag_service.ingest_documents("cwe", CWE_ENTRIES)

    # MITRE ATT&CK
    counts["mitre_attack"] = await rag_service.ingest_documents(
        "mitre_attack", MITRE_ENTRIES
    )

    logger.info("✅ Security knowledge base loaded", counts=counts)
    return counts


# Allow running as script: python -m app.knowledge.security_kb
if __name__ == "__main__":
    import asyncio

    async def main():
        rag = RAGService()
        await rag.initialize()
        counts = await load_security_knowledge_base(rag)
        print(f"Loaded: {counts}")

    asyncio.run(main())
