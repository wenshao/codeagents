#!/usr/bin/env python3
"""Check github_repo fields against GitHub API to catch repo mapping errors.

Reads agents-metadata.json. For each agent with a github_repo and stars field,
fetches the repo from GitHub API and verifies the stars count is within a
tolerance (default 2x). This catches issues like wrong repo mappings.

Usage:
    python3 scripts/check_repo_url.py              # full check with API
    python3 scripts/check_repo_url.py --no-api     # schema-only check (fast)
"""

import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "docs" / "data" / "agents-metadata.json"

# Stars mismatch beyond this ratio triggers a MAJOR error.
MAJOR_RATIO = 2.0


def load_data():
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def parse_compact_stars(s: str) -> int | None:
    """Parse compact star strings like '130k', '~133k', '21k' to int."""
    if not s or s in ("-", "—", "unknown"):
        return None
    m = re.match(r"~?\s*(\d+(?:\.\d+)?)\s*[kK万]?", s.strip())
    if not m:
        return None
    num = float(m.group(1))
    if "k" in s.lower() or "K" in s:
        num *= 1000
    elif "万" in s:
        num *= 10000
    return int(num)


def fetch_github_stars(owner: str, repo: str) -> int | None:
    """Fetch stargazers_count from GitHub API with retry."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "codeagents-check/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("stargazers_count")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # repo not found
            if e.code == 403:
                # rate limited
                wait = min(60, 10 * (attempt + 1))
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if e.code >= 500:
                time.sleep(5 * (attempt + 1))
                continue
            return None
        except Exception:
            time.sleep(3)
            continue
    return None


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Check github_repo and Stars consistency")
    parser.add_argument("--no-api", action="store_true", help="Skip GitHub API calls (fast, schema-only)")
    args = parser.parse_args()

    data = load_data()

    errors = []
    warnings = []

    for agent in data.get("agents", []):
        agent_id = agent.get("id", "unknown")
        github_repo = agent.get("github_repo")
        stars_str = agent.get("stars", "")

        if not github_repo:
            warnings.append(f"{agent_id}: no github_repo configured")
            continue

        # Validate repo format
        parts = github_repo.split("/")
        if len(parts) != 2 or not all(parts):
            errors.append(f"{agent_id}: invalid github_repo format: {github_repo}")
            continue

        if args.no_api:
            continue

        # Skip if no stars to compare
        metadata_stars = parse_compact_stars(stars_str)
        if metadata_stars is None:
            continue

        github_stars = fetch_github_stars(parts[0], parts[1])
        if github_stars is None:
            errors.append(f"{agent_id}: cannot fetch GitHub repo {github_repo}")
            continue

        ratio = metadata_stars / github_stars if github_stars > 0 else float("inf")

        if ratio > MAJOR_RATIO or ratio < 1 / MAJOR_RATIO:
            errors.append(
                f"{agent_id}: MAJOR Stars mismatch: "
                f"metadata={stars_str} ({metadata_stars}) vs GitHub={github_stars} "
                f"(ratio={ratio:.1f}x, threshold={MAJOR_RATIO}x)"
            )
        elif ratio > 1.5 or ratio < 0.67:
            warnings.append(
                f"{agent_id}: Stars possibly stale: "
                f"metadata={stars_str} ({metadata_stars}) vs GitHub={github_stars} "
                f"(ratio={ratio:.1f}x)"
            )

        # Rate limit: sleep between API calls
        time.sleep(1)

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  ERROR: {e}")
    if warnings:
        for w in warnings:
            print(f"  WARN: {w}")

    if errors:
        print(f"\nFAILED: {len(errors)} error(s) found")
        return 1

    print("OK: repository URL checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
