"""
seed_demo.py — Seed the default demo memory dataset into the configured DB.

Why this exists:
- Production deploys should keep runtime startup simple and predictable.
- Seeding is a one-time content operation, so it is better as an explicit script.
"""

from pathlib import Path

import ingest


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    reasons_file = root / "demo-repo" / "memory_reasons.json"

    if not reasons_file.exists():
        raise FileNotFoundError(f"Could not find demo data file: {reasons_file}")

    count = ingest.ingest(reasons_file, clear=True)
    print(f"Seeded demo dataset successfully. Inserted {count} memories.")


if __name__ == "__main__":
    main()
