"""Compatibility wrapper for the canonical cross-language test path."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

if __name__ == "__main__":
    import runpy

    runpy.run_module("tests.cross_language.cross_validate", run_name="__main__")
else:
    from tests.cross_language.cross_validate import *
