"""Top-level convenience wrapper for factory load ingestion CLI."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "integration"))

from ingest_factory_load import main  # noqa: E402

if __name__ == "__main__":
    main()
