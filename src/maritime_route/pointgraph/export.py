"""Drawing and export of the results of a session.

The same drawing functions are used by the map and convergence tabs of the
GUI and by the export, so the saved PNG files look exactly like the screen.

Files written by :func:`export_session` (``<prefix>`` is a time stamp):

=================================  ==========================================
``<prefix>_map.png``               map with the points and all routes
``<prefix>_convergence.png``       convergence curve of the genetic algorithm
``<prefix>_routes.geojson``        routes as GeoJSON LineStrings (+ end points)
``<prefix>_routes.csv``            waypoints of every route
``<prefix>_comparison.csv``        comparison table of the algorithms
``<prefix>_log.json``              all parameters and results (machine-readable)
``<prefix>_log.txt``               the same in readable form
``<prefix>_map.html``              interactive folium map (if folium is installed)
=================================  ==========================================
"""
from __future__ import annotations

import csv
import datetime as _dt
import json
import math
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure

from ..config import CLASS_COLOR, CLASS_NAMES, SERIES_COLOR
from .session import ALGORITHM_LABEL, CourseSession

#: Line style of every algorithm on the map: (colour, width, style, z-order).
ROUTE_STYLE = {
    "dijkstra": (SERIES_COLOR["tertiary"], 4.0, "-", 5),
    "astar": (SERIES_COLOR["quaternary"], 1.6, "--", 6),
    "genetic": (SERIES_COLOR["secondary"], 2.0, "-", 7),
}
#: Human-readable class labels for legends.
CLASS_LABEL = {"OPEN_SEA": "Open sea", "COASTAL_SEA": "Coastal sea",
               "NEAR_COAST": "Near coast (land)", "COASTLINE": "Inland"}


def draw_map(fig: Figure, session: CourseSession, show_edges: bool = False,
             max_points: int = 60000, title: Optional[str] = None) -> None:
    """Draw points, optional graph edges, end points and routes on ``fig``."""
    fig.clear()
    ax = fig.add_subplot(111)
    sea, points = session.sea, session.points
    if points is None:
        ax.text(0.5, 0.5, "Load a dataset (File > Open dataset)", ha="center", va="center",
                transform=ax.transAxes)
        ax.set_axis_off()
        return
    if sea is not None:
        lat_min, lat_max, lon_min, lon_max = sea.bbox
    elif session.start is not None and session.goal is not None:
        from .session import route_area
        lat_min, lat_max, lon_min, lon_max = route_area(session.start, session.goal, 2.0)
    else:
        lat_min, lat_max, lon_min, lon_max = (float(points.lat.min()), float(points.lat.max()),
                                              float(points.lon.min()), float(points.lon.max()))
    mask = points.in_bbox((lat_min, lat_max, lon_min, lon_max))
    idx = np.nonzero(mask)[0]
    if idx.size > max_points:                       # thin out very dense views
        idx = np.random.default_rng(0).choice(idx, max_points, replace=False)
    size = 2.0 if idx.size < 15000 else 0.8
    for k, name in enumerate(CLASS_NAMES):
        sel = idx[points.cls[idx] == k]
        ax.scatter(points.lon[sel], points.lat[sel], s=size, c=CLASS_COLOR[name],
                   label=CLASS_LABEL[name], linewidths=0, zorder=1)
    if show_edges and sea is not None:
        edges = np.array(sea.graph.edges())
        if edges.size:
            segs = np.stack((np.column_stack((sea.lon[edges[:, 0]], sea.lat[edges[:, 0]])),
                             np.column_stack((sea.lon[edges[:, 1]], sea.lat[edges[:, 1]]))), axis=1)
            ax.add_collection(LineCollection(segs, colors="#9a9a96", linewidths=0.25,
                                             alpha=0.6, zorder=2))
    for name in ("dijkstra", "astar", "genetic"):
        run = session.runs.get(name)
        if run is None or not run.coords:
            continue
        colour, width, style, z = ROUTE_STYLE[name]
        lat = [c[0] for c in run.coords]
        lon = [c[1] for c in run.coords]
        label = f"{ALGORITHM_LABEL[name]}: {run.breakdown['length_km']:.0f} km, cost {run.result.cost:.1f}"
        ax.plot(lon, lat, style, color=colour, lw=width, label=label, zorder=z,
                solid_capstyle="round")
    if session.start is not None:
        ax.plot(session.start[1], session.start[0], marker="o", ms=9, color="#1f1f1d",
                mfc="white", mew=2, zorder=9, ls="none", label="Departure")
    if session.goal is not None:
        ax.plot(session.goal[1], session.goal[0], marker="s", ms=9, color="#1f1f1d",
                mfc="white", mew=2, zorder=9, ls="none", label="Destination")
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_aspect(1.0 / max(math.cos(math.radians(0.5 * (lat_min + lat_max))), 0.1))
    ax.set_xlabel("Longitude, deg (WGS-84)")
    ax.set_ylabel("Latitude, deg (WGS-84)")
    ax.grid(color=SERIES_COLOR["grid"], lw=0.5, zorder=0)
    if title:
        ax.set_title(title, fontsize=10)
    legend = ax.legend(loc="best", fontsize=7, framealpha=0.9)
    for handle in legend.legend_handles:
        if hasattr(handle, "set_sizes"):
            handle.set_sizes([20])
    fig.tight_layout()


def draw_convergence(fig: Figure, session: CourseSession, title: Optional[str] = None) -> None:
    """Best and median population cost per generation of the last GA run."""
    fig.clear()
    ax = fig.add_subplot(111)
    run = session.runs.get("genetic")
    if run is None or not run.result.best_history:
        ax.text(0.5, 0.5, "Run the genetic algorithm to see its convergence",
                ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return
    best = run.result.best_history
    median = run.result.median_history
    gens = np.arange(len(best))
    ax.plot(gens, median, color=SERIES_COLOR["primary"], lw=1.2, label="Median cost of the population")
    ax.plot(gens, best, color=SERIES_COLOR["secondary"], lw=2.0, label="Best cost")
    optimum = session.optimum()
    if optimum is not None:
        ax.axhline(optimum, color=SERIES_COLOR["neutral"], lw=1.0, ls="--",
                   label=f"Optimum (Dijkstra / A*) = {optimum:.1f}")
    top = float(np.percentile(median, 98)) if len(median) > 5 else float(max(median))
    low = min(best) if optimum is None else min(min(best), optimum)
    ax.set_ylim(low - 0.03 * (top - low + 1), top)
    ax.set_xlabel("Generation")
    ax.set_ylabel("Route cost F, weighted km")
    ax.grid(color=SERIES_COLOR["grid"], lw=0.5)
    ax.legend(fontsize=8)
    if title:
        ax.set_title(title, fontsize=10)
    fig.tight_layout()


def _clean(value):
    """JSON-friendly copy: NaN/inf -> None, tuples -> lists, numpy -> Python."""
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, (np.floating, float)):
        value = float(value)
        return value if math.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    return value


def routes_geojson(session: CourseSession) -> Dict:
    """GeoJSON FeatureCollection with the routes and the two end points."""
    features: List[Dict] = []
    for name, run in session.runs.items():
        if not run.coords:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[lon, lat] for lat, lon in run.coords]},
            "properties": _clean({"algorithm": name, "cost": run.result.cost, **run.breakdown,
                                  "n_nodes": len(run.coords), "runtime_s": run.result.runtime_s}),
        })
    for label, pos in (("departure", session.start), ("destination", session.goal)):
        if pos is not None:
            features.append({"type": "Feature",
                             "geometry": {"type": "Point", "coordinates": [pos[1], pos[0]]},
                             "properties": {"role": label}})
    return {"type": "FeatureCollection", "features": features}


def log_text(session: CourseSession) -> str:
    """Readable parameter and result log."""
    info = _clean(session.describe())
    lines = [f"Ship course search - run log ({_dt.datetime.now():%Y-%m-%d %H:%M:%S})", ""]
    for key, value in info.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            lines += [f"    {k} = {v}" for k, v in value.items()]
        else:
            lines.append(f"{key} = {value}")
    lines += ["", "Results:"]
    for row in session.comparison_rows():
        lines.append("    " + ", ".join(f"{k} = {_fmt(v)}" for k, v in row.items()))
    return "\n".join(lines) + "\n"


def _fmt(value) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def export_session(session: CourseSession, folder: Path | str,
                   map_figure: Optional[Figure] = None,
                   convergence_figure: Optional[Figure] = None,
                   prefix: Optional[str] = None) -> List[Path]:
    """Write all result files of the session into ``folder``.

    Parameters
    ----------
    session:
        Session with at least one finished run.
    folder:
        Target directory (created if needed).
    map_figure, convergence_figure:
        Figures to save; new figures are drawn when omitted.
    prefix:
        File name prefix; a time stamp by default.

    Returns
    -------
    list of Path
        The files written.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    prefix = prefix or f"course_{_dt.datetime.now():%Y%m%d_%H%M%S}"
    written: List[Path] = []

    if map_figure is None:
        map_figure = Figure(figsize=(10, 7))
        draw_map(map_figure, session)
    path = folder / f"{prefix}_map.png"
    map_figure.savefig(path, dpi=200)
    written.append(path)

    if "genetic" in session.runs:
        if convergence_figure is None:
            convergence_figure = Figure(figsize=(8, 5))
            draw_convergence(convergence_figure, session)
        path = folder / f"{prefix}_convergence.png"
        convergence_figure.savefig(path, dpi=200)
        written.append(path)

    path = folder / f"{prefix}_routes.geojson"
    path.write_text(json.dumps(routes_geojson(session), indent=1), encoding="utf-8")
    written.append(path)

    path = folder / f"{prefix}_routes.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["algorithm", "index", "latitude", "longitude"])
        for name, run in session.runs.items():
            for i, (lat, lon) in enumerate(run.coords):
                writer.writerow([name, i, f"{lat:.6f}", f"{lon:.6f}"])
    written.append(path)

    rows = session.comparison_rows()
    path = folder / f"{prefix}_comparison.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        if rows:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(_clean(rows))
    written.append(path)

    log = _clean({"session": session.describe(), "results": rows,
                  "convergence": {"best": session.runs["genetic"].result.best_history,
                                  "median": session.runs["genetic"].result.median_history}
                  if "genetic" in session.runs else None})
    path = folder / f"{prefix}_log.json"
    path.write_text(json.dumps(log, indent=1), encoding="utf-8")
    written.append(path)
    path = folder / f"{prefix}_log.txt"
    path.write_text(log_text(session), encoding="utf-8")
    written.append(path)

    html = folium_map(session)
    if html is not None:
        path = folder / f"{prefix}_map.html"
        html.save(str(path))
        written.append(path)
    return written


def folium_map(session: CourseSession):
    """Interactive web map of the routes, or ``None`` without folium."""
    try:
        import folium
    except ImportError:
        return None
    if not session.runs or session.start is None or session.goal is None:
        return None
    centre = [(session.start[0] + session.goal[0]) / 2, (session.start[1] + session.goal[1]) / 2]
    fmap = folium.Map(location=centre, zoom_start=6, tiles="OpenStreetMap")
    for name, run in session.runs.items():
        if run.coords:
            colour, width, style, _ = ROUTE_STYLE[name]
            folium.PolyLine(run.coords, color=colour, weight=width + 1,
                            dash_array="8" if style == "--" else None,
                            tooltip=f"{ALGORITHM_LABEL[name]}: {run.breakdown['length_km']:.0f} km").add_to(fmap)
    folium.Marker(session.start, tooltip="Departure").add_to(fmap)
    folium.Marker(session.goal, tooltip="Destination").add_to(fmap)
    return fmap
