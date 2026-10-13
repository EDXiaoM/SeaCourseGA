"""Entry point of the desktop application."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
    """Parse the command line, create the Qt application and show the window."""
    parser = argparse.ArgumentParser(description="Ship course search on open-sea points (genetic algorithm)")
    parser.add_argument("--dataset", type=Path, default=None,
                        help="labelled point file to open at start-up (default: data/raw/merged.json)")
    args = parser.parse_args(argv)

    import matplotlib
    matplotlib.use("Qt5Agg")
    from PyQt5.QtWidgets import QApplication

    from .main_window import MainWindow

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Sea Course GA")
    window = MainWindow(dataset=args.dataset)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
