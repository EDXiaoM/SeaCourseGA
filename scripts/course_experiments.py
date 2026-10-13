"""Experiments of the course project (section 3.4 of the explanatory note).

Runs every experiment reported in the note on the full labelled dataset and
writes the numbers to ``docs/course/results.json`` and the figures to
``docs/course/figures/``. All runs use the classes of
:mod:`maritime_route.pointgraph`, i.e. exactly the code of the desktop
application.

Experiments
-----------
1. Dataset summary (loading and cleaning).
2. Graph statistics of every preset voyage, by distance and by visibility.
3. Dijkstra, A* and the genetic algorithm (10 seeds) on every voyage.
4. Routes of the distance graph that cross land (visibility check).
5. Influence of the penalty weights on the optimal route.
6. Sensitivity of the genetic algorithm to its parameters and operators.

Usage::

    python scripts/course_experiments.py                    # about 20 minutes on one CPU core
    python scripts/course_experiments.py --seeds 3 --quick  # shortened run for a smoke test
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
from matplotlib.figure import Figure  # noqa: E402

from maritime_route.config import CLASS_COLOR, CLASS_NAMES, RAW_DIR, SERIES_COLOR  # noqa: E402
from maritime_route.pointgraph import (  # noqa: E402
    VOYAGES, CostWeights, CourseSession, GAConfig, GraphConfig, apply_costs, build_graph,
    dijkstra_path, route_area, route_breakdown,
)
from maritime_route.pointgraph.export import CLASS_LABEL, draw_convergence, draw_map  # noqa: E402
from maritime_route.pointgraph.graph import segment_visible, to_xyz  # noqa: E402

OUT = ROOT / "docs" / "course"
FIG = OUT / "figures"


def short(name: str) -> str:
    """Voyage name without the sea area in brackets."""
    return name.split(" (")[0]


def ga_stats(session: CourseSession, config: GAConfig, seeds, optimum: float) -> dict:
    """Run the GA with several seeds; summary of gap, time, effort."""
    gaps, times, evals, gens, lengths = [], [], [], [], []
    for seed in seeds:
        run = session.run("genetic", replace(config, seed=seed))
        r = run.result
        gaps.append(100.0 * (r.cost - optimum) / optimum)
        times.append(r.runtime_s)
        evals.append(r.expanded)
        gens.append(r.generated)
        lengths.append(run.breakdown["length_km"])
    return {
        "gap_mean": statistics.mean(gaps), "gap_min": min(gaps), "gap_max": max(gaps),
        "gap_sd": statistics.pstdev(gaps), "within_1pct": sum(g <= 1.0 for g in gaps),
        "time_mean": statistics.mean(times), "evaluations_mean": statistics.mean(evals),
        "generations_mean": statistics.mean(gens), "length_mean": statistics.mean(lengths),
        "gaps": gaps, "n": len(gaps),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dataset", type=Path, default=RAW_DIR / "merged.json")
    parser.add_argument("--seeds", type=int, default=10, help="GA runs per voyage")
    parser.add_argument("--quick", action="store_true", help="fewer sensitivity runs")
    args = parser.parse_args()
    FIG.mkdir(parents=True, exist_ok=True)
    results: dict = {"machine": {"python": platform.python_version(), "platform": platform.platform(),
                                 "processor": platform.processor() or platform.machine()}}

    # 1. dataset -----------------------------------------------------------
    session = CourseSession()
    summary = session.load(args.dataset)
    results["dataset"] = {k: v for k, v in summary.__dict__.items()}
    print(summary.as_text(), flush=True)
    points = session.points
    regions, counts = np.unique(points.region, return_counts=True)
    results["dataset"]["regions"] = {str(r): int(c) for r, c in zip(regions, counts)}
    fig = Figure(figsize=(11, 5.2))
    ax = fig.add_subplot(111)
    for k, name in enumerate(CLASS_NAMES):
        sel = points.cls == k
        ax.scatter(points.lon[sel], points.lat[sel], s=0.15, c=CLASS_COLOR[name], linewidths=0,
                   label=f"{CLASS_LABEL[name]} ({int(sel.sum())})")
    for v in VOYAGES:
        ax.plot([v.start[1], v.goal[1]], [v.start[0], v.goal[0]], "-", color="#1f1f1d", lw=0.8)
    ax.set_xlabel("Longitude, deg (WGS-84)")
    ax.set_ylabel("Latitude, deg (WGS-84)")
    ax.grid(color=SERIES_COLOR["grid"], lw=0.5)
    legend = ax.legend(loc="lower left", fontsize=8, markerscale=1)
    for h in legend.legend_handles:
        h.set_sizes([25])
    fig.tight_layout()
    fig.savefig(FIG / "fig_dataset_map.png", dpi=220)

    seeds = list(range(args.seeds))
    base_ga = GAConfig()
    weights = CostWeights()
    session.set_weights(weights)
    voyages = []

    # 2-4. voyages ------------------------------------------------------------
    for voyage in VOYAGES:
        print(f"\n== {voyage.name}", flush=True)
        session.set_endpoints(voyage.start, voyage.goal)
        entry = {"name": voyage.name, "start": voyage.start, "goal": voyage.goal}
        # distance graph first: its Dijkstra route is checked for land crossings
        sea_d = session.build_graph(GraphConfig(mode="distance"))
        entry["graph_distance"] = sea_d.stats.to_dict()
        d_run = session.run("dijkstra")
        path = d_run.result.path
        xyz = to_xyz(sea_d.lat, sea_d.lon)
        land_xyz = to_xyz(sea_d.land_lat, sea_d.land_lon)
        a = np.array(path[:-1]); b = np.array(path[1:])
        lengths = np.array([sea_d.graph.edges[u, v]["length"] for u, v in zip(a, b)])
        vis = segment_visible(xyz[a], xyz[b], lengths, xyz, land_xyz, 1.0)
        entry["distance_route"] = {"cost": d_run.result.cost, **d_run.breakdown,
                                   "edges": int(len(a)), "edges_crossing_land": int((~vis).sum()),
                                   "km_crossing_land": float(lengths[~vis].sum())}
        sea = session.build_graph(GraphConfig(mode="visibility"))
        entry["graph_visibility"] = sea.stats.to_dict()
        entry["snap_km"] = session.snap_km
        for name in ("dijkstra", "astar"):
            run = session.run(name)
            r = run.result
            entry[name] = {"cost": r.cost, "expanded": r.expanded, "generated": r.generated,
                           "runtime_s": r.runtime_s, "nodes": len(r.path), **run.breakdown}
        # median of five timings for the fast exact searches
        for name in ("dijkstra", "astar"):
            timing = []
            for _ in range(5):
                timing.append(session.run(name).result.runtime_s)
            entry[name]["runtime_median_s"] = statistics.median(timing)
        optimum = entry["dijkstra"]["cost"]
        entry["genetic"] = ga_stats(session, base_ga, seeds, optimum)
        print(f"  optimum {optimum:.1f}; GA gap mean {entry['genetic']['gap_mean']:.2f} % "
              f"(max {entry['genetic']['gap_max']:.2f}), time {entry['genetic']['time_mean']:.1f} s", flush=True)
        # one reference run (seed 0) for the figures
        session.run("dijkstra"); session.run("astar"); session.run("genetic", replace(base_ga, seed=0))
        tag = short(voyage.name).replace(" - ", "_").replace(" ", "")
        fig = Figure(figsize=(9, 6.5))
        draw_map(fig, session)
        fig.savefig(FIG / f"fig_route_{tag}.png", dpi=220)
        fig = Figure(figsize=(8, 4.6))
        draw_convergence(fig, session)
        fig.savefig(FIG / f"fig_conv_{tag}.png", dpi=220)
        entry["reference_run"] = {"best_history": session.runs["genetic"].result.best_history,
                                  "median_history": session.runs["genetic"].result.median_history}
        voyages.append(entry)
    results["voyages"] = voyages

    # graph zoom figure: distance vs visibility near Cape Agulhas
    bbox = (-35.2, -33.8, 18.2, 20.6)
    fig = Figure(figsize=(11, 4.6))
    for i, mode in enumerate(("distance", "visibility")):
        ax = fig.add_subplot(1, 2, i + 1)
        sea = build_graph(points, bbox, GraphConfig(mode=mode))
        for k, name in enumerate(CLASS_NAMES):
            sel = points.in_bbox(bbox) & (points.cls == k)
            ax.scatter(points.lon[sel], points.lat[sel], s=3, c=CLASS_COLOR[name], linewidths=0, zorder=3)
        from matplotlib.collections import LineCollection
        e = np.array(sea.graph.edges())
        segs = np.stack((np.column_stack((sea.lon[e[:, 0]], sea.lat[e[:, 0]])),
                         np.column_stack((sea.lon[e[:, 1]], sea.lat[e[:, 1]]))), axis=1)
        ax.add_collection(LineCollection(segs, colors="#7a7a76", linewidths=0.3, zorder=2))
        ax.set_xlim(bbox[2], bbox[3]); ax.set_ylim(bbox[0], bbox[1])
        ax.set_aspect(1 / np.cos(np.radians(-34.5)))
        ax.set_title(f"{'a' if i == 0 else 'b'}) by {mode}: {sea.stats.n_edges} edges", fontsize=10)
        ax.set_xlabel("Longitude, deg")
        if i == 0:
            ax.set_ylabel("Latitude, deg")
    fig.tight_layout()
    fig.savefig(FIG / "fig_graph_modes.png", dpi=220)

    # bar chart: nodes expanded by Dijkstra and A*
    fig = Figure(figsize=(9, 4.2))
    ax = fig.add_subplot(111)
    x = np.arange(len(voyages))
    ax.bar(x - 0.2, [v["dijkstra"]["expanded"] for v in voyages], 0.38,
           color=SERIES_COLOR["tertiary"], label="Dijkstra", edgecolor="white", linewidth=1)
    ax.bar(x + 0.2, [v["astar"]["expanded"] for v in voyages], 0.38,
           color=SERIES_COLOR["quaternary"], label="A*", edgecolor="white", linewidth=1)
    ax.set_xticks(x, [short(v["name"]).replace(" - ", "-\n") for v in voyages], fontsize=8)
    ax.set_ylabel("Nodes expanded")
    ax.grid(axis="y", color=SERIES_COLOR["grid"], lw=0.5)
    ax.set_axisbelow(True)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig_expanded.png", dpi=220)

    # 5. penalty weights --------------------------------------------------------
    penalty = []
    voyage = VOYAGES[4]                                   # Cape Town - Gqeberha
    session.set_endpoints(voyage.start, voyage.goal)
    session.build_graph(GraphConfig())
    for alpha, beta in ((0.0, 0.0), (0.5, 0.0), (0.0, 2.0), (0.5, 2.0), (2.0, 5.0)):
        session.set_weights(CostWeights(alpha, beta, 10.0))
        run = session.run("dijkstra")
        penalty.append({"alpha": alpha, "beta": beta, "cost": run.result.cost, **run.breakdown})
    results["penalties"] = {"voyage": voyage.name, "rows": penalty}
    session.set_weights(weights)

    # 6. sensitivity -------------------------------------------------------------
    sens_seeds = seeds[:3] if args.quick else seeds[:5]
    sensitivity = {}
    for voyage in (VOYAGES[4], VOYAGES[1]):               # hardest and a medium case
        session.set_endpoints(voyage.start, voyage.goal)
        session.build_graph(GraphConfig())
        optimum = session.run("dijkstra").result.cost
        block = {}
        for label, values, field in (("population_size", (20, 50, 100, 150), "population_size"),
                                     ("mutation_rate", (0.1, 0.3, 0.5, 0.7), "mutation_rate"),
                                     ("crossover_rate", (0.5, 0.8, 0.95), "crossover_rate")):
            rows = []
            for value in values:
                stats = ga_stats(session, replace(base_ga, **{field: value}), sens_seeds, optimum)
                rows.append({"value": value, **{k: stats[k] for k in ("gap_mean", "gap_min", "gap_max", "time_mean", "evaluations_mean")}})
                print(f"  {short(voyage.name)} {label}={value}: gap {stats['gap_mean']:.2f} %", flush=True)
            block[label] = rows
        rows = []
        for label, cfg in (("full operator set", base_ga),
                           ("without intermediate nodes", replace(base_ga, via_share=0.0)),
                           ("without shortcut mutation", replace(base_ga, shortcut_share=0.0)),
                           ("without crossover", replace(base_ga, crossover_rate=0.0))):
            stats = ga_stats(session, cfg, sens_seeds, optimum)
            rows.append({"variant": label, **{k: stats[k] for k in ("gap_mean", "gap_min", "gap_max", "time_mean")}})
            print(f"  {short(voyage.name)} {label}: gap {stats['gap_mean']:.2f} %", flush=True)
        block["operators"] = rows
        sensitivity[voyage.name] = block
    results["sensitivity"] = {"seeds": sens_seeds, "blocks": sensitivity}

    fig = Figure(figsize=(10, 3.8))
    colours = [SERIES_COLOR["secondary"], SERIES_COLOR["primary"]]
    for i, key in enumerate(("population_size", "mutation_rate")):
        ax = fig.add_subplot(1, 2, i + 1)
        for colour, (vname, block) in zip(colours, sensitivity.items()):
            xs = [r["value"] for r in block[key]]
            ys = [r["gap_mean"] for r in block[key]]
            ax.plot(xs, ys, "o-", color=colour, lw=2, ms=6, label=short(vname))
        ax.set_xlabel("Population size" if key == "population_size" else "Mutation probability")
        ax.set_ylabel("Mean gap to optimum, %")
        ax.set_ylim(bottom=0)
        ax.grid(color=SERIES_COLOR["grid"], lw=0.5)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig_sensitivity.png", dpi=220)

    (OUT / "results.json").write_text(json.dumps(results, indent=1, default=float), encoding="utf-8")
    print(f"\nResults written to {OUT / 'results.json'}")


if __name__ == "__main__":
    t0 = time.perf_counter()
    main()
    print(f"Total time {time.perf_counter() - t0:.0f} s")
