# seed-data

This folder holds a **copy** of the demo `memory_reasons.json` that is committed to the **main** MemoryOS repo.

**Why it exists:** `demo-repo/` may be a nested git repository. Nested repos are often not included in the parent repo’s GitHub checkout, so Render (and other hosts) would not see `demo-repo/memory_reasons.json`. The file here is always present after clone, so `core/seed_demo.py` and service startup seeding work with zero submodule setup.

Keep this file in sync when you change the canonical narrative in `demo-repo/` (or edit here and copy back if you prefer).
