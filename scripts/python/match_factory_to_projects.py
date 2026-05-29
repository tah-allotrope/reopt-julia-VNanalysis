from pathlib import Path
import runpy

TARGET = Path(__file__).resolve().parent / "integration" / "match_factory_to_projects.py"
runpy.run_path(str(TARGET), run_name="__main__")
