"""State of one working session of the desktop application.

:class:`CourseSession` keeps the loaded dataset, the current graph, the
departure and destination and the results of the last runs. The GUI and the
experiment script use the same class, so every number reported in the
explanatory note is produced by exactly the code the user runs.

Typical sequence::

    session = CourseSession()
    session.load("data/raw/merged.json")
    session.set_endpoints((46.45, 30.80), (41.65, 41.60))
    session.build_graph(GraphConfig(), area=None)      # area around the route
    session.set_weights(CostWeights())
    session.run("dijkstra"); session.run("astar"); session.run("genetic", GAConfig())
    session.comparison_rows()
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .cost import CostWeights, apply_costs, route_breakdown
from .dataset import BBox, LoadSummary, PointSet, load_points
from .genetic import GAConfig, GAProgress, StopFlag, genetic_path
from .graph import GraphConfig, ProgressFn, SeaGraph, build_graph
from .search import PathResult, astar_path, dijkstra_path

Coordinate = Tuple[float, float]

#: Algorithms offered by the application, in display order.
ALGORITHMS: Tuple[str, ...] = ("genetic", "dijkstra", "astar")
#: Display names of the algorithms.
ALGORITHM_LABEL: Dict[str, str] = {"genetic": "Genetic algorithm", "dijkstra": "Dijkstra", "astar": "A*"}


@dataclass(frozen=True)
class Voyage:
    """A predefined voyage (preset) of the application."""

    name: str
    start: Coordinate
    goal: Coordinate


#: Voyages in parts of the dataset with dense water coverage. They are the
#: presets of the GUI and the test cases of ``scripts/course_experiments.py``.
VOYAGES: Tuple[Voyage, ...] = (
    Voyage("Odesa - Batumi (Black Sea)", (46.45, 30.80), (41.65, 41.60)),
    Voyage("Varna - Sinop (Black Sea)", (43.19, 28.00), (42.03, 35.17)),
    Voyage("Burgas - Trabzon (Black Sea)", (42.48, 27.55), (41.02, 39.75)),
    Voyage("Sanya - Muara (South China Sea)", (18.20, 109.50), (5.00, 114.95)),
    Voyage("Cape Town - Gqeberha (South Africa)", (-33.90, 18.40), (-33.95, 25.65)),
    Voyage("Dubai - Muscat (Strait of Hormuz)", (25.30, 55.25), (23.65, 58.60)),
    Voyage("Colon - Limon (Caribbean Sea)", (9.40, -79.90), (10.00, -83.02)),
)


def route_area(start: Coordinate, goal: Coordinate, margin_deg: float) -> BBox:
    """Rectangle around two positions enlarged by ``margin_deg`` degrees."""
    return (max(-90.0, min(start[0], goal[0]) - margin_deg),
            min(90.0, max(start[0], goal[0]) + margin_deg),
            max(-180.0, min(start[1], goal[1]) - margin_deg),
            min(180.0, max(start[1], goal[1]) + margin_deg))


@dataclass
class RouteRun:
    """One finished run of an algorithm, ready for display and export."""

    result: PathResult
    breakdown: Dict[str, float] = field(default_factory=dict)
    coords: List[Coordinate] = field(default_factory=list)
    parameters: Dict = field(default_factory=dict)

    @property
    def algorithm(self) -> str:
        return self.result.algorithm


class CourseSession:
    """Dataset, graph, end points, cost weights and results of one session."""

    def __init__(self) -> None:
        self.points: Optional[PointSet] = None
        self.load_summary: Optional[LoadSummary] = None
        self.dataset_path: Optional[Path] = None
        self.sea: Optional[SeaGraph] = None
        self.weights: CostWeights = CostWeights()
        self.start: Optional[Coordinate] = None
        self.goal: Optional[Coordinate] = None
        self.start_node: Optional[int] = None
        self.goal_node: Optional[int] = None
        self.snap_km: Tuple[float, float] = (math.nan, math.nan)
        self.runs: Dict[str, RouteRun] = {}
        self.ga_config: GAConfig = GAConfig()

    # ------------------------------------------------------------------ data
    def load(self, path: Path | str, clean: bool = True) -> LoadSummary:
        """Load a labelled dataset; drops the graph and all results."""
        points, summary = load_points(path, clean=clean)
        self.points, self.load_summary = points, summary
        self.dataset_path = Path(path)
        self.sea = None
        self.runs.clear()
        return summary

    # ----------------------------------------------------------------- graph
    def set_endpoints(self, start: Coordinate, goal: Coordinate) -> None:
        """Set departure and destination; snaps them if a graph exists."""
        self.start, self.goal = start, goal
        self.runs.clear()
        if self.sea is not None:
            self._snap()

    def build_graph(self, config: GraphConfig, area: Optional[BBox] = None,
                    margin_deg: float = 2.0, progress: ProgressFn = None) -> SeaGraph:
        """Build the graph of ``area`` (default: around the current route)."""
        if self.points is None:
            raise RuntimeError("Load a dataset first")
        if area is None:
            if self.start is None or self.goal is None:
                raise RuntimeError("Set the departure and the destination first")
            area = route_area(self.start, self.goal, margin_deg)
        self.sea = build_graph(self.points, area, config, progress)
        apply_costs(self.sea, self.weights)
        self.runs.clear()
        if self.start is not None and self.goal is not None:
            self._snap()
        return self.sea

    def set_weights(self, weights: CostWeights) -> None:
        """Change the penalty weights; edge costs are recomputed."""
        self.weights = weights
        if self.sea is not None:
            apply_costs(self.sea, weights)
        self.runs.clear()

    def _snap(self) -> None:
        """Attach departure and destination to the nearest graph nodes.

        Both ends are first snapped to their nearest nodes. When these lie in
        different connected components (for example one end in a closed bay),
        both are snapped to the largest component instead.
        """
        assert self.sea is not None and self.start is not None and self.goal is not None
        s, ds = self.sea.nearest_node(*self.start)
        g, dg = self.sea.nearest_node(*self.goal)
        if self.sea.component[s] != self.sea.component[g]:
            s, ds = self.sea.nearest_node(*self.start, largest_only=True)
            g, dg = self.sea.nearest_node(*self.goal, largest_only=True)
        self.start_node, self.goal_node = s, g
        self.snap_km = (ds, dg)

    # ------------------------------------------------------------- searches
    def run(self, algorithm: str, ga_config: Optional[GAConfig] = None,
            progress: GAProgress = None, should_stop: StopFlag = None) -> RouteRun:
        """Run one algorithm between the snapped end nodes."""
        if self.sea is None or self.start_node is None or self.goal_node is None:
            raise RuntimeError("Build the graph and set the route first")
        graph, s, g = self.sea.graph, self.start_node, self.goal_node
        parameters: Dict = {}
        if algorithm == "dijkstra":
            result = dijkstra_path(graph, s, g)
        elif algorithm == "astar":
            result = astar_path(graph, s, g)
        elif algorithm == "genetic":
            config = ga_config or self.ga_config
            self.ga_config = config
            parameters = config.to_dict()
            result = genetic_path(graph, s, g, config, progress=progress, should_stop=should_stop)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        run = RouteRun(result=result, parameters=parameters)
        if result.found:
            run.breakdown = route_breakdown(graph, result.path, self.weights)
            run.coords = self.sea.coords(result.path)
        self.runs[algorithm] = run
        return run

    def optimum(self) -> Optional[float]:
        """Optimal cost from Dijkstra or A* if one of them has been run."""
        for name in ("dijkstra", "astar"):
            run = self.runs.get(name)
            if run is not None and run.result.found:
                return run.result.cost
        return None

    def comparison_rows(self) -> List[Dict]:
        """One row per finished run, with the gap to the optimum in percent."""
        optimum = self.optimum()
        rows = []
        for name in ALGORITHMS:
            run = self.runs.get(name)
            if run is None:
                continue
            r, b = run.result, run.breakdown
            gap = None
            if r.found and optimum:
                gap = 100.0 * (r.cost - optimum) / optimum
            rows.append({
                "algorithm": ALGORITHM_LABEL[name],
                "found": r.found,
                "cost": r.cost if r.found else None,
                "length_km": b.get("length_km"),
                "coastal_km": b.get("coastal_km"),
                "danger_km": b.get("danger_km"),
                "min_land_km": b.get("min_land_km"),
                "nodes": len(r.path),
                "effort": r.expanded,
                "runtime_s": r.runtime_s,
                "gap_pct": gap,
            })
        return rows

    def describe(self) -> Dict:
        """Everything needed to reproduce the session, for the parameter log."""
        info: Dict = {
            "dataset": str(self.dataset_path) if self.dataset_path else None,
            "start": self.start, "goal": self.goal,
            "start_node": self.start_node, "goal_node": self.goal_node,
            "snap_km": self.snap_km,
            "cost_weights": self.weights.to_dict(),
            "ga_config": self.ga_config.to_dict(),
        }
        if self.load_summary is not None:
            info["load_summary"] = {k: v for k, v in self.load_summary.__dict__.items()}
        if self.sea is not None:
            info["graph_area"] = self.sea.bbox
            info["graph_config"] = self.sea.config.to_dict()
            info["graph_stats"] = self.sea.stats.to_dict()
        return info
