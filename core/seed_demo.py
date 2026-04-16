"""
seed_demo.py — Seed the default demo memory dataset into the configured DB.

Resolution order for the reasons file:
1. MEMORYOS_SEED_PATH — absolute or repo-root-relative path (optional env).
2. seed-data/memory_reasons.json — tracked in the main repo (hosting-friendly).
3. demo-repo/memory_reasons.json — local narrative repo (may be missing on deploy).

Why seed-data exists:
- demo-repo/ can be its own git repo; GitHub may not ship its contents inside the parent repo.
- A copy under seed-data/ avoids submodules and keeps Render/Vercel deploys frictionless.
"""

import os
from pathlib import Path

import ingest


def _resolve_reasons_file(root: Path) -> Path:
    env = os.getenv("MEMORYOS_SEED_PATH", "").strip()
    if env:
        p = Path(env)
        if not p.is_absolute():
            p = root / p
        return p

    candidates = [
        root / "seed-data" / "memory_reasons.json",
        root / "demo-repo" / "memory_reasons.json",
    ]
    for p in candidates:
        if p.exists():
            return p

    # Prefer seed path in error message for deploy clarity
    return root / "seed-data" / "memory_reasons.json"


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    reasons_file = _resolve_reasons_file(root)

    if not reasons_file.exists():
        raise FileNotFoundError(
            f"Could not find demo data file. Tried MEMORYOS_SEED_PATH, "
            f"seed-data/memory_reasons.json, demo-repo/memory_reasons.json. "
            f"Last path checked: {reasons_file}"
        )

    count = ingest.ingest(reasons_file, clear=True)
    print(f"Seeded demo dataset successfully from {reasons_file}. Inserted {count} memories.")


if __name__ == "__main__":
    main()
