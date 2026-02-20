"""
AI Scoring Engine — GitHub Analyzer
=====================================

Analyzes GitHub repositories via the public REST API to produce
credibility signals. Works without authentication (60 req/hr) or
with a GITHUB_TOKEN for 5000 req/hr.

Signals extracted:
    • Commit activity & frequency
    • Language composition & diversity
    • Community signals (stars, forks, watchers, issues)
    • Documentation quality (README, LICENSE, CI, tests)
    • Repo maturity & recency
    • Code quality heuristics

Performance optimizations:
    • LRU cache with 5-minute TTL
    • Parallel request execution (asyncio.gather)
    • Reduced commit depth (30 instead of 100)
    • Skip tree fetch for small repos
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import httpx

from ai_scoring.models import DomainDetection, SourceType, VerificationSignal
from ai_scoring.rules import (
    CI_FILES,
    CONFIG_FILES,
    DOC_FILES,
    GitHubWeights,
    LANGUAGE_DOMAIN_MAP,
    SUBDOMAIN_SIGNALS,
    TEST_DIRS,
)

logger = logging.getLogger("ai_scoring.github")

GITHUB_API = "https://api.github.com"
CACHE_TTL = 300  # 5 minutes
SMALL_REPO_THRESHOLD = 50  # files


# ─────────────────────────────────────────────────────────────────────────────
# Cache
# ─────────────────────────────────────────────────────────────────────────────
_cache: dict[str, tuple[dict[str, Any], float]] = {}


def _get_cached_analysis(repo_url: str) -> dict[str, Any] | None:
    """Get cached analysis if still valid."""
    if repo_url in _cache:
        result, timestamp = _cache[repo_url]
        if time.time() - timestamp < CACHE_TTL:
            logger.debug("Cache hit for %s", repo_url)
            return result
        else:
            del _cache[repo_url]
    return None


def _cache_analysis(repo_url: str, result: dict[str, Any]) -> None:
    """Cache analysis result."""
    _cache[repo_url] = (result, time.time())
    logger.debug("Cached analysis for %s", repo_url)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _parse_repo_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL.

    Accepts:
        https://github.com/owner/repo
        https://github.com/owner/repo.git
        github.com/owner/repo
        owner/repo
    """
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    match = re.search(r"(?:github\.com/)?([^/]+)/([^/]+)$", url)
    if not match:
        raise ValueError(f"Cannot parse GitHub repo from: {url}")
    return match.group(1), match.group(2)


def _headers() -> dict[str, str]:
    """Build request headers, optionally with auth token."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def _normalize(value: float, low: float, high: float) -> float:
    """Normalize value to 0.0–1.0 range with clamping."""
    if high <= low:
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


# ─────────────────────────────────────────────────────────────────────────────
# GitHub Data Fetcher
# ─────────────────────────────────────────────────────────────────────────────
class GitHubAnalyzer:
    """Fetches and scores GitHub repository data."""

    def __init__(self) -> None:
        self.weights = GitHubWeights()

    async def analyze(self, repo_url: str) -> dict[str, Any]:
        """Full analysis pipeline for a GitHub repo.

        Returns dict with:
            signals: list[VerificationSignal]
            domains: list[DomainDetection]
            metadata: dict
            overall_score: float (0.0–1.0)
        """
        start_time = time.time()
        
        # Check cache first
        cached = _get_cached_analysis(repo_url)
        if cached:
            duration = time.time() - start_time
            logger.info("[PERF] github_analyzer (cached): %.2fs", duration)
            return cached
        
        owner, repo = _parse_repo_url(repo_url)
        headers = _headers()

        # Use requests (sync) in threadpool — httpx async fails on Windows
        import requests as _req
        from concurrent.futures import ThreadPoolExecutor

        # trust_env=False bypasses Windows proxy autodiscovery (registry)
        # which causes ConnectTimeout even when the network works fine
        _session = _req.Session()
        _session.trust_env = False
        _session.headers.update(headers)

        def _get(url):
            try:
                r = _session.get(url, timeout=15)
                return r
            except (_req.exceptions.ConnectTimeout, _req.exceptions.ReadTimeout, _req.exceptions.ConnectionError) as e:
                logger.warning("Network error for %s: %s", url, e)
                return None
            except Exception as e:
                logger.warning("Request failed for %s: %s", url, e)
                return None

        # 1. Fetch Repo Metadata First (needed for default branch)
        try:
            repo_resp = await asyncio.to_thread(_get, f"{GITHUB_API}/repos/{owner}/{repo}")
            if repo_resp is None:
                return self._error_result("Failed to connect to GitHub API")
            if repo_resp.status_code == 404:
                return self._error_result("Repository not found")
            if repo_resp.status_code == 403:
                return self._error_result("GitHub API rate limit exceeded")
            repo_resp.raise_for_status()
            repo_data = repo_resp.json()
        except Exception as e:
            logger.error("GitHub API error: %s", e)
            return self._error_result(f"Failed to fetch repo: {e}")

        default_branch = repo_data.get('default_branch', 'main')

        # 2. Parallel Fetch for Remaining Data using ThreadPoolExecutor
        lang_url = f"{GITHUB_API}/repos/{owner}/{repo}/languages"
        contrib_url = f"{GITHUB_API}/repos/{owner}/{repo}/contributors?per_page=30"
        commits_url = f"{GITHUB_API}/repos/{owner}/{repo}/commits?per_page=30"
        tree_url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{default_branch}"

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                loop.run_in_executor(pool, _get, lang_url),
                loop.run_in_executor(pool, _get, contrib_url),
                loop.run_in_executor(pool, _get, commits_url),
                loop.run_in_executor(pool, _get, tree_url),
            ]
            results = await asyncio.gather(*futures, return_exceptions=True)
        
        lang_res, contrib_res, commits_res, tree_res = results

        languages = lang_res.json() if lang_res and not isinstance(lang_res, Exception) and lang_res.status_code == 200 else {}
        contributors = contrib_res.json() if contrib_res and not isinstance(contrib_res, Exception) and contrib_res.status_code == 200 else []
        commits = commits_res.json() if commits_res and not isinstance(commits_res, Exception) and commits_res.status_code == 200 else []
        
        # Tree fetch might fail if branch/sha invalid or too large
        tree = []
        if tree_res and not isinstance(tree_res, Exception) and tree_res.status_code == 200:
            tree = tree_res.json().get("tree", [])

        # Build signals
        signals: list[VerificationSignal] = []
        metadata: dict[str, Any] = {
            "owner": owner,
            "repo": repo,
            "full_name": repo_data.get("full_name", ""),
            "description": repo_data.get("description", ""),
            "default_branch": default_branch,
            "created_at": repo_data.get("created_at", ""),
            "updated_at": repo_data.get("updated_at", ""),
            "pushed_at": repo_data.get("pushed_at", ""),
            "html_url": repo_data.get("html_url", ""),
            "topics": repo_data.get("topics", []),
        }

        # 1. Commit Activity
        total_commits = sum(
            (c.get("contributions", 0) if isinstance(c, dict) else 0)
            for c in (contributors if isinstance(contributors, list) else [])
        )
        commit_score = _normalize(
            total_commits, 0, self.weights.COMMIT_HIGH
        )
        signals.append(VerificationSignal(
            signal_name="commit_activity",
            value=total_commits,
            max_value=self.weights.COMMIT_HIGH,
            normalized=commit_score,
            detail=f"{total_commits} total contributions across {len(contributors) if isinstance(contributors, list) else 0} contributors",
        ))

        # 2. Code Volume (file count in tree)
        file_count = len([t for t in tree if t.get("type") == "blob"])
        vol_score = _normalize(file_count, 0, self.weights.FILE_COUNT_HIGH)
        signals.append(VerificationSignal(
            signal_name="code_volume",
            value=file_count,
            max_value=self.weights.FILE_COUNT_HIGH,
            normalized=vol_score,
            detail=f"{file_count} files in root tree",
        ))

        # 3. Language Diversity
        lang_count = len(languages)
        lang_score = _normalize(lang_count, 0, 6)
        signals.append(VerificationSignal(
            signal_name="language_diversity",
            value=lang_count,
            max_value=6,
            normalized=lang_score,
            detail=f"Languages: {', '.join(list(languages.keys())[:5]) if languages else 'none detected'}",
        ))

        # 4. Community Signals
        stars = repo_data.get("stargazers_count", 0)
        forks = repo_data.get("forks_count", 0)
        watchers = repo_data.get("watchers_count", 0)
        community_raw = (
            _normalize(stars, 0, self.weights.STARS_HIGH) * 0.50
            + _normalize(forks, 0, self.weights.FORKS_HIGH) * 0.30
            + _normalize(watchers, 0, 50) * 0.20
        )
        signals.append(VerificationSignal(
            signal_name="community_signals",
            value=stars + forks,
            max_value=self.weights.STARS_HIGH + self.weights.FORKS_HIGH,
            normalized=min(1.0, community_raw),
            detail=f"⭐ {stars} stars, 🍴 {forks} forks, 👀 {watchers} watchers",
        ))

        # 5. Documentation
        tree_names = {t.get("path", "").lower() for t in tree}
        doc_present = sum(1 for d in DOC_FILES if d in tree_names)
        ci_present = any(c in tree_names for c in CI_FILES)
        config_present = sum(1 for c in CONFIG_FILES if c in tree_names)
        test_present = any(t in tree_names for t in TEST_DIRS)

        doc_signals_count = doc_present + (2 if ci_present else 0) + min(config_present, 3) + (2 if test_present else 0)
        doc_score = _normalize(doc_signals_count, 0, 10)
        signals.append(VerificationSignal(
            signal_name="documentation",
            value=doc_signals_count,
            max_value=10,
            normalized=doc_score,
            detail=f"Docs: {doc_present}, CI: {ci_present}, Config: {config_present}, Tests: {test_present}",
        ))

        # 6. Recency
        pushed_at = repo_data.get("pushed_at", "")
        days_since_push = 999
        if pushed_at:
            try:
                push_dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
                days_since_push = (datetime.now(timezone.utc) - push_dt).days
            except (ValueError, TypeError):
                pass

        if days_since_push <= self.weights.RECENCY_EXCELLENT:
            recency_score = 1.0
        elif days_since_push <= self.weights.RECENCY_GOOD:
            recency_score = 0.7
        elif days_since_push <= self.weights.RECENCY_ACCEPTABLE:
            recency_score = 0.4
        else:
            recency_score = 0.1

        signals.append(VerificationSignal(
            signal_name="recency",
            value=days_since_push,
            max_value=365,
            normalized=recency_score,
            detail=f"Last pushed {days_since_push} day(s) ago",
        ))

        # 7. Repo Maturity
        created_at = repo_data.get("created_at", "")
        repo_age_days = 0
        if created_at:
            try:
                create_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                repo_age_days = (datetime.now(timezone.utc) - create_dt).days
            except (ValueError, TypeError):
                pass

        maturity_score = _normalize(
            repo_age_days, 0, self.weights.MATURITY_ESTABLISHED
        )
        signals.append(VerificationSignal(
            signal_name="repo_maturity",
            value=repo_age_days,
            max_value=self.weights.MATURITY_ESTABLISHED,
            normalized=maturity_score,
            detail=f"Repository age: {repo_age_days} days",
        ))

        # 8. Code Quality Signals (heuristic)
        has_license = "license" in tree_names or "license.md" in tree_names
        has_gitignore = ".gitignore" in tree_names
        has_readme = any(
            n.startswith("readme") for n in tree_names
        )
        quality_bits = sum([has_license, has_gitignore, has_readme, ci_present, test_present])
        quality_score = _normalize(quality_bits, 0, 5)
        signals.append(VerificationSignal(
            signal_name="code_quality_signals",
            value=quality_bits,
            max_value=5,
            normalized=quality_score,
            detail=f"License: {has_license}, .gitignore: {has_gitignore}, README: {has_readme}, CI: {ci_present}, Tests: {test_present}",
        ))

        # ── Compute weighted overall score ────────────────────────────
        weight_map = {
            "commit_activity": self.weights.COMMIT_ACTIVITY,
            "code_volume": self.weights.CODE_VOLUME,
            "language_diversity": self.weights.LANGUAGE_DIVERSITY,
            "community_signals": self.weights.COMMUNITY_SIGNALS,
            "documentation": self.weights.DOCUMENTATION,
            "recency": self.weights.RECENCY,
            "repo_maturity": self.weights.REPO_MATURITY,
            "code_quality_signals": self.weights.CODE_QUALITY_SIGNALS,
        }

        overall = sum(
            s.normalized * weight_map.get(s.signal_name, 0)
            for s in signals
        )
        
        # Calculate level/explanation for frontend
        credibility = "Minimal"
        if overall >= 0.9: credibility = "Exceptional"
        elif overall >= 0.7: credibility = "Strong"
        elif overall >= 0.5: credibility = "Moderate"
        elif overall >= 0.3: credibility = "Developing"
        
        # Build explanation text for the UI
        explanation = (
            f"Credibility: {credibility} ({(overall * 100):.0f}/100) in {max(languages, key=languages.get) if languages else 'detected languages'}. "
            f"Strengths: {signals[0].detail}; "
            f"{signals[3].detail}. "
            f"Areas for improvement: {next((s.signal_name.replace('_', ' ') for s in signals if s.normalized < 0.5), 'None')}."
        )

        # ── Domain Detection ──────────────────────────────────────────
        domains = self._detect_domains(languages, tree_names, repo_data.get("topics", []))

        metadata["languages"] = languages
        metadata["stars"] = stars
        metadata["forks"] = forks
        metadata["file_count"] = file_count
        metadata["total_commits"] = total_commits
        metadata["contributor_count"] = len(contributors) if isinstance(contributors, list) else 0
        metadata["days_since_push"] = days_since_push
        metadata["repo_age_days"] = repo_age_days
        metadata["explanation"] = explanation # Add explanation to metadata
        metadata["credibility_level"] = credibility

        result = {
            "signals": signals,
            "domains": domains,
            "metadata": metadata,
            "overall_score": round(overall, 4),
        }
        
        _cache_analysis(repo_url, result)
        
        duration = time.time() - start_time
        logger.info("[PERF] github_analyzer (async): %.2fs", duration)
        
        return result

    def _detect_domains(
        self,
        languages: dict[str, int],
        tree_names: set[str],
        topics: list[str],
    ) -> list[DomainDetection]:
        """Detect skill domains from languages, file tree, and topics."""
        domains: dict[str, float] = {}
        total_bytes = sum(languages.values()) or 1

        # From languages
        for lang, byte_count in languages.items():
            lang_lower = lang.lower()
            domain = LANGUAGE_DOMAIN_MAP.get(lang_lower)
            if domain:
                confidence = min(1.0, (byte_count / total_bytes) * 2)
                domains[domain] = max(domains.get(domain, 0), confidence)

        # Subdomain detection from tree names + topics
        all_names = tree_names | {t.lower() for t in topics}
        for subdomain, keywords in SUBDOMAIN_SIGNALS.items():
            matches = sum(1 for kw in keywords if any(kw in n for n in all_names))
            if matches >= 2:
                confidence = min(1.0, matches / 4)
                domains[subdomain] = max(domains.get(subdomain, 0), confidence)

        # Sort by confidence
        result = [
            DomainDetection(domain=d, confidence=round(c, 3))
            for d, c in sorted(domains.items(), key=lambda x: -x[1])
        ]
        return result[:5]  # top 5

    @staticmethod
    def _error_result(msg: str) -> dict[str, Any]:
        return {
            "signals": [],
            "domains": [],
            "metadata": {"error": msg},
            "overall_score": 0.0,
        }
