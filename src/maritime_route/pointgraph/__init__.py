"""Point-graph route search of the course project.

Course project "Application for finding the optimal course of a sea vessel
over open-sea points based on a genetic algorithm". The package searches a
ship's course on a graph whose nodes are the labelled water points of the
dataset (WGS-84, four classes) and compares a genetic algorithm with the exact
Dijkstra and A* searches. It does not use the neural network or the lattice of
the diploma project; only the data loader, the cleaning rule and the geodesy
helpers are shared.

Modules
-------
dataset
    Reading and cleaning of the labelled point file (:class:`PointSet`).
graph
    Graph construction by distance or by visibility (:class:`SeaGraph`).
cost
    Edge cost and fitness function (length + penalties).
search
    Dijkstra and A* on the point graph (:class:`PathResult`).
genetic
    The genetic algorithm (:class:`GAConfig`, :func:`genetic_path`).
session
    State of one working session, voyage presets.
export
    Map and convergence drawings, export of routes, plots and logs.
"""
from .cost import CostWeights, apply_costs, route_breakdown
from .dataset import LoadSummary, PointSet, load_points
from .genetic import GAConfig, genetic_path
from .graph import GraphConfig, SeaGraph, build_graph
from .search import PathResult, astar_path, dijkstra_path
from .session import ALGORITHMS, VOYAGES, CourseSession, Voyage, route_area

__all__ = [
    "CostWeights", "apply_costs", "route_breakdown", "LoadSummary", "PointSet",
    "load_points", "GAConfig", "genetic_path", "GraphConfig", "SeaGraph",
    "build_graph", "PathResult", "astar_path", "dijkstra_path", "ALGORITHMS",
    "VOYAGES", "CourseSession", "Voyage", "route_area",
]
