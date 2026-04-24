"""
batch_ingest.py — Walk a local git repo's history and extract structured memory per commit.

Usage
-----
    python batch_ingest.py --repo-path <path> --repo-name <name> [options]

Options
-------
  --repo-path   PATH   Path to local git repository (required)
  --repo-name   NAME   Name to store in DB (required)
  --branch          REF   Branch/ref to walk (default: HEAD)
  --limit           INT   Max commits to process, most recent first (default: 20)
  --skip-merges           Skip merge commits (default: on; --no-skip-merges to disable)
  --skip-patterns   LIST  Comma-separated substrings; commits whose first line contains
                          any match are skipped (default: '⬆ Bump,📝 Update release
                          notes,🔖 Release version')
  --db              PATH  Path to SQLite database (default: core/memories.db)
"""

import argparse
import json
import logging
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import git

sys.path.insert(0, str(Path(__file__).parent))
import store
from extractor import get_extractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_LOGS_DIR = Path(__file__).parent.parent / "logs"


def _already_ingested(repo_name: str, commit_hash: str, db_path: Path) -> bool:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM memories WHERE repo = ? AND commit_hash = ? LIMIT 1",
            (repo_name, commit_hash),
        ).fetchone()
    return row is not None


def _get_diff_text(repo: git.Repo, commit: git.Commit) -> str:
    try:
        if commit.parents:
            return repo.git.diff(commit.parents[0].hexsha, commit.hexsha)
        # Initial commit — diff against empty tree
        return repo.git.diff_tree("--no-commit-id", "-p", "-r", commit.hexsha)
    except Exception as exc:
        logger.debug("Could not get diff for %s: %s", commit.hexsha[:7], exc)
        return ""


def _is_fallback(memory: dict) -> bool:
    return memory["tradeoffs"]["chosen"].startswith("Not determined")


def _trunc(text: str, n: int = 60) -> str:
    return text[:n] + "…" if len(text) > n else text


def run(
    repo_path: Path,
    repo_name: str,
    limit: int,
    skip_merges: bool,
    db_path: Path,
    branch: str = "HEAD",
    skip_patterns: list[str] | None = None,
) -> dict:
    if skip_patterns is None:
        skip_patterns = []
    store.init_db(db_path=db_path)
    extractor = get_extractor()
    repo = git.Repo(repo_path)

    commits = list(repo.iter_commits(branch, max_count=limit))
    logger.info(
        "Repo: %s  |  branch: %s  |  commits to examine: %d  (limit=%d)",
        repo_name, branch, len(commits), limit,
    )

    run_start = time.monotonic()
    total = extracted = fallbacks = skipped = 0
    per_commit_log: list[dict] = []

    for commit in commits:
        short = commit.hexsha[:7]
        first_line = commit.message.strip().splitlines()[0]
        label = _trunc(first_line)

        # --- skip: merge commit ---
        if skip_merges and len(commit.parents) > 1:
            logger.info("  %s  %-62s  skipped (merge)", short, label)
            total += 1
            skipped += 1
            per_commit_log.append({
                "hash": short,
                "message": label,
                "status": "skipped",
                "duration_ms": 0,
                "decision_type": None,
            })
            continue

        # --- skip: pattern match ---
        matched = next((p for p in skip_patterns if p in first_line), None)
        if matched:
            logger.info("  %s  %-62s  skipped (pattern match: %r)", short, label, matched)
            total += 1
            skipped += 1
            per_commit_log.append({
                "hash": short,
                "message": label,
                "status": "skipped",
                "skip_reason": "pattern match",
                "duration_ms": 0,
                "decision_type": None,
            })
            continue

        # --- skip: already in DB ---
        if _already_ingested(repo_name, commit.hexsha, db_path):
            logger.info("  %s  %-62s  skipped (duplicate)", short, label)
            total += 1
            skipped += 1
            per_commit_log.append({
                "hash": short,
                "message": label,
                "status": "skipped",
                "duration_ms": 0,
                "decision_type": None,
            })
            continue

        diff = _get_diff_text(repo, commit)

        t0 = time.monotonic()
        memory = extractor.extract(diff=diff, message=first_line)
        duration_ms = round((time.monotonic() - t0) * 1000)

        memory["commit_hash"] = commit.hexsha
        is_fb = _is_fallback(memory)
        status = "fallback" if is_fb else "extracted"

        store.insert_memory(
            repo=repo_name,
            commit_hash=memory["commit_hash"],
            commit_message=memory["commit_message"],
            reason=memory["reason"],
            decision_type=memory["decision_type"],
            tradeoffs=memory["tradeoffs"],
            tags=memory["tags"],
            db_path=db_path,
        )

        logger.info("  %s  %-62s  %s  (%dms)", short, label, status, duration_ms)

        total += 1
        if is_fb:
            fallbacks += 1
        else:
            extracted += 1

        per_commit_log.append({
            "hash": short,
            "message": label,
            "status": status,
            "duration_ms": duration_ms,
            "decision_type": memory["decision_type"],
        })

    processed = extracted + fallbacks
    avg_ms = round((time.monotonic() - run_start) * 1000 / processed) if processed else 0

    print(
        f"\nDone.  total={total}  extracted={extracted}  "
        f"fallbacks={fallbacks}  skipped={skipped}"
    )

    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    summary = {
        "repo_name": repo_name,
        "branch": branch,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_commits_processed": total,
        "extracted_count": extracted,
        "fallback_count": fallbacks,
        "skipped_count": skipped,
        "avg_extraction_time_ms": avg_ms,
        "per_commit": per_commit_log,
    }
    log_path = _LOGS_DIR / f"ingest_run_{ts}.json"
    log_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Run summary written to %s", log_path)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract structured memory from a local git repo's commit history."
    )
    parser.add_argument("--repo-path", required=True, type=Path)
    parser.add_argument("--repo-name", required=True)
    parser.add_argument("--branch", default="HEAD", help="Branch/ref to walk (default: HEAD)")
    parser.add_argument("--limit", type=int, default=20, help="Max commits (default: 20)")
    parser.add_argument(
        "--skip-merges",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip merge commits (default: on)",
    )
    parser.add_argument("--db", type=Path, default=None)
    args = parser.parse_args()

    if not args.repo_path.exists():
        print(f"Error: repo path does not exist: {args.repo_path}", file=sys.stderr)
        sys.exit(1)

    db_path = args.db or Path(__file__).parent / "memories.db"

    run(
        repo_path=args.repo_path,
        repo_name=args.repo_name,
        limit=args.limit,
        skip_merges=args.skip_merges,
        db_path=db_path,
        branch=args.branch,
    )


if __name__ == "__main__":
    main()
