"""
ingest.py — Load a memory_reasons.json file into SQLite.

Usage
-----
    python ingest.py <path_to_memory_reasons.json> [--db <path>] [--clear]

Flags
-----
  --db <path>   Path to the SQLite database (default: memories.db next to this file)
  --clear       Wipe existing memories for this repo before ingesting
"""

import json
import sys
from pathlib import Path

# Allow running from any working directory
sys.path.insert(0, str(Path(__file__).parent))
import store


def ingest(json_path: Path, db_path: Path | None = None, clear: bool = False) -> int:
    """Load memories from *json_path* into SQLite. Returns number of rows inserted."""
    kwargs = {"db_path": db_path} if db_path else {}

    store.init_db(**kwargs)

    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)

    repo = data["repo"]
    memories = data["memories"]

    if clear:
        deleted = store.clear_repo(repo, **kwargs)
        print(f"Cleared {deleted} existing memories for repo '{repo}'.")

    print(f"Ingesting {len(memories)} memories into repo '{repo}' …\n")

    for mem in memories:
        row_id = store.insert_memory(
            repo=repo,
            commit_hash=mem["commit_hash"],
            commit_message=mem["commit_message"],
            reason=mem["reason"],
            decision_type=mem["decision_type"],
            tradeoffs=mem["tradeoffs"],
            tags=mem["tags"],
            **kwargs,
        )
        short_hash = mem["commit_hash"][:7]
        print(f"  [{row_id}] {short_hash}  {mem['decision_type']:<30}  {mem['commit_message']}")

    print(f"\nDone. {len(memories)} memories stored.")
    return len(memories)


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    json_path = Path(args[0])
    if not json_path.exists():
        print(f"Error: file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    db_path = None
    clear = False
    i = 1
    while i < len(args):
        if args[i] == "--db" and i + 1 < len(args):
            db_path = Path(args[i + 1])
            i += 2
        elif args[i] == "--clear":
            clear = True
            i += 1
        else:
            print(f"Unknown argument: {args[i]}", file=sys.stderr)
            sys.exit(1)

    ingest(json_path, db_path=db_path, clear=clear)


if __name__ == "__main__":
    main()
