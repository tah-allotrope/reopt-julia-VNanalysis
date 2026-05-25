"""Convenience wrapper for procurement comparison CLI."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "integration"))
from compare_procurement import main
main()
