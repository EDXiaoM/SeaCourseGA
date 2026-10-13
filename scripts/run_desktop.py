"""Start the desktop application of the course project.

Usage::

    python scripts/run_desktop.py                      # opens data/raw/merged.json if present
    python scripts/run_desktop.py --dataset my_points.geojson
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from maritime_route.desktop.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
