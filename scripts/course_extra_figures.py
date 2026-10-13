"""Additional figures of the explanatory note (course project).

* ``fig_distance_vs_visibility.png`` - optimal Dijkstra routes of the voyage
  Varna - Sinop on the graph built by distance and on the graph built by
  visibility; the first one cuts across land.
* ``fig_convergence_pair.png`` - convergence of the reference GA runs (seed 0)
  for Odesa - Batumi and Cape Town - Gqeberha, read from
  ``docs/course/results.json`` written by ``course_experiments.py``.

Usage::

    python scripts/course_extra_figures.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
from matplotlib.figure import Figure  # noqa: E402

from maritime_route.config import CLASS_COLOR, CLASS_NAMES, RAW_DIR, SERIES_COLOR  # noqa: E402
from maritime_route.pointgraph import VOYAGES, CourseSession, GraphConfig  # noqa: E402
from maritime_route.pointgraph.export import CLASS_LABEL  # noqa: E402

OUT = ROOT / "docs" / "course"
FIG = OUT / "figures"


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    session = CourseSession()
    session.load(RAW_DIR / "merged.json")
    voyage = VOYAGES[1]                                   # Varna - Sinop
    session.set_endpoints(voyage.start, voyage.goal)
    routes = {}
    for mode in ("distance", "visibility"):
        session.build_graph(GraphConfig(mode=mode))
        run = session.run("dijkstra")
        routes[mode] = (run.coords, run.breakdown["length_km"])
    bbox = session.sea.bbox
    pts = session.points
    fig = Figure(figsize=(10, 5.2))
    ax = fig.add_subplot(111)
    mask = pts.in_bbox(bbox)
    for k, name in enumerate(CLASS_NAMES):
        sel = mask & (pts.cls == k)
        ax.scatter(pts.lon[sel], pts.lat[sel], s=1.2, c=CLASS_COLOR[name], linewidths=0,
                   label=CLASS_LABEL[name])
    styles = {"distance": (SERIES_COLOR["secondary"], "--", "graph by distance"),
              "visibility": (SERIES_COLOR["tertiary"], "-", "graph by visibility")}
    for mode, (coords, length) in routes.items():
        colour, ls, label = styles[mode]
        ax.plot([c[1] for c in coords], [c[0] for c in coords], ls, color=colour, lw=2.2,
                label=f"Dijkstra, {label}: {length:.0f} km")
    ax.plot(voyage.start[1], voyage.start[0], "o", ms=9, mfc="white", mec="#1f1f1d", mew=2, label="Departure")
    ax.plot(voyage.goal[1], voyage.goal[0], "s", ms=9, mfc="white", mec="#1f1f1d", mew=2, label="Destination")
    ax.set_xlim(bbox[2], bbox[3]); ax.set_ylim(bbox[0], bbox[1])
    ax.set_aspect(1 / np.cos(np.radians(0.5 * (bbox[0] + bbox[1]))))
    ax.set_xlabel("Longitude, deg (WGS-84)"); ax.set_ylabel("Latitude, deg (WGS-84)")
    ax.grid(color=SERIES_COLOR["grid"], lw=0.5)
    leg = ax.legend(fontsize=7.5, loc="upper right")
    for h in leg.legend_handles:
        if hasattr(h, "set_sizes"):
            h.set_sizes([20])
    fig.tight_layout()
    fig.savefig(FIG / "fig_distance_vs_visibility.png", dpi=220)

    results = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    fig = Figure(figsize=(11, 4.0))
    for i, idx in enumerate((0, 4)):
        v = results["voyages"][idx]
        ref = v["reference_run"]
        best, median = ref["best_history"], ref["median_history"]
        ax = fig.add_subplot(1, 2, i + 1)
        g = np.arange(len(best))
        ax.plot(g, median, color=SERIES_COLOR["primary"], lw=1.1, label="Median cost of the population")
        ax.plot(g, best, color=SERIES_COLOR["secondary"], lw=2.0, label="Best cost")
        opt = v["dijkstra"]["cost"]
        ax.axhline(opt, color=SERIES_COLOR["neutral"], ls="--", lw=1.0, label=f"Optimum = {opt:.1f}")
        top = float(np.percentile(median, 97))
        ax.set_ylim(opt - 0.02 * (top - opt), top)
        ax.set_xlabel("Generation"); ax.set_ylabel("Route cost F")
        ax.set_title(f"{'a' if i == 0 else 'b'}) {v['name'].split(' (')[0]}", fontsize=10)
        ax.grid(color=SERIES_COLOR["grid"], lw=0.5)
        ax.legend(fontsize=7.5)
    fig.tight_layout()
    fig.savefig(FIG / "fig_convergence_pair.png", dpi=220)
    print("written:", FIG / "fig_distance_vs_visibility.png", FIG / "fig_convergence_pair.png")


if __name__ == "__main__":
    main()
