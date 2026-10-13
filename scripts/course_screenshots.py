"""Screenshots of the desktop application for the explanatory note.

The window is driven through its own slots (load, build graph, run all
algorithms) exactly as a user would do with the mouse; the widgets are then
grabbed into PNG files. Works without a display (``QT_QPA_PLATFORM=offscreen``).

Usage::

    QT_QPA_PLATFORM=offscreen python scripts/course_screenshots.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib  # noqa: E402

matplotlib.use("Qt5Agg")
from PyQt5.QtWidgets import QApplication  # noqa: E402

from maritime_route.desktop.main_window import MainWindow  # noqa: E402

OUT = ROOT / "docs" / "course" / "screenshots"


def wait(app: QApplication, window: MainWindow, timeout: float = 600.0) -> None:
    """Process events until the background task of the window has finished."""
    t0 = time.time()
    while True:
        app.processEvents()
        thread = window.thread
        if thread is None or (thread.isFinished() and not thread.isRunning()):
            break
        if time.time() - t0 > timeout:
            raise TimeoutError("background task did not finish")
        time.sleep(0.02)
    for _ in range(20):
        app.processEvents()
        time.sleep(0.01)


def grab(widget, name: str) -> None:
    widget.grab().save(str(OUT / name))
    print("written", OUT / name)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv[:1])
    window = MainWindow(dataset=Path("/nonexistent"))      # start empty
    window.resize(1500, 950)
    window.show()
    app.processEvents()
    grab(window, "ui_01_start.png")

    window.load_dataset(ROOT / "data" / "raw" / "merged.json")
    wait(app, window)
    window.preset.setCurrentIndex(0)                       # Odesa - Batumi
    window.show_edges.setChecked(True)
    window.start_build()
    wait(app, window)
    grab(window, "ui_02_graph.png")

    window.show_edges.setChecked(False)
    window.start_runs(["dijkstra", "astar", "genetic"])
    # start_runs may first rebuild the graph and then chain the runs
    for _ in range(3):
        wait(app, window)
    window.tabs.setCurrentIndex(0)
    app.processEvents()
    grab(window, "ui_03_routes.png")
    window.tabs.setCurrentIndex(1)
    app.processEvents()
    grab(window, "ui_04_convergence.png")
    window.tabs.setCurrentIndex(2)
    app.processEvents()
    grab(window, "ui_05_comparison.png")
    window.tabs.setCurrentIndex(3)
    app.processEvents()
    grab(window, "ui_06_log.png")
    # lower part of the control panel (penalties, GA parameters, run buttons)
    window.tabs.setCurrentIndex(0)
    scroll = window.centralWidget().widget(0)
    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
    app.processEvents()
    grab(window, "ui_07_panel_bottom.png")
    out = ROOT / "outputs" / "screenshot_export"
    files = window.session and __import__(
        "maritime_route.pointgraph.export", fromlist=["export_session"]).export_session(
        window.session, out, window.map_canvas.figure, window.conv_canvas.figure, prefix="odesa_batumi")
    print("exported", [f.name for f in files])
    window.close()


if __name__ == "__main__":
    main()
