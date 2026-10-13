"""Dijkstra and A* on the point graph.

Both searches were first written by the author for the regular lattice of the
diploma project (:mod:`maritime_route.routing.dijkstra` and
:mod:`maritime_route.routing.astar`). Here they are ported to an arbitrary
weighted graph: the 8-neighbourhood of a lattice cell is replaced by the
adjacency list of a node, and the pre-computed step-length table by the edge
attribute ``weight``. The structure of the algorithms is unchanged:

* the open list is a binary heap with lazy deletion (``heapq`` has no
  decrease-key, so an improved distance is pushed as a new entry and stale
  entries are skipped when popped);
* a node is final the first time it is popped (all costs are positive and the
  A* heuristic is consistent);
* the search stops as soon as the goal is popped.

A* uses ``h(n) = d_gc(n, goal)``, the great-circle distance to the goal. Every
edge cost is at least the edge length (see :mod:`.cost`), and the sum of the
edge lengths of any path is at least the great-circle distance between its
ends, so ``h`` never over-estimates the remaining cost (admissible) and
satisfies ``h(u) <= c(u, v) + h(v)`` (consistent). A* therefore returns the
same optimal cost as Dijkstra while expanding fewer nodes.
"""
from __future__ import annotations

import heapq
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import networkx as nx

from ..config import EARTH_RADIUS_KM


@dataclass
class PathResult:
    """Outcome of one route search (any of the three algorithms).

    Attributes
    ----------
    algorithm:
        ``"genetic"``, ``"dijkstra"`` or ``"astar"``.
    found:
        True if a path from the start to the goal was found.
    path:
        Node ids from the start to the goal.
    cost:
        Sum of edge costs (weighted km); ``inf`` if not found.
    expanded:
        Dijkstra/A*: nodes taken from the heap. GA: fitness evaluations.
    generated:
        Dijkstra/A*: heap insertions. GA: generations run.
    runtime_s:
        Wall-clock time, seconds.
    best_history, median_history:
        GA only - best and median population cost after every generation.
    message:
        Human-readable outcome.
    """

    algorithm: str
    found: bool
    path: List[int] = field(default_factory=list)
    cost: float = math.inf
    expanded: int = 0
    generated: int = 0
    runtime_s: float = 0.0
    best_history: List[float] = field(default_factory=list)
    median_history: List[float] = field(default_factory=list)
    message: str = ""


def _reconstruct(came_from: Dict[int, int], goal: int) -> List[int]:
    """Follow predecessor links back from the goal and reverse the list."""
    path = [goal]
    while path[-1] in came_from:
        path.append(came_from[path[-1]])
    path.reverse()
    return path


def dijkstra_path(graph: nx.Graph, start: int, goal: int, weight: str = "weight") -> PathResult:
    """Uniform-cost search for the cheapest path between two nodes.

    Parameters
    ----------
    graph:
        Undirected graph whose edges carry the attribute ``weight``.
    start, goal:
        Node ids.
    weight:
        Name of the edge attribute holding the cost.

    Returns
    -------
    PathResult
    """
    t0 = time.perf_counter()
    if start not in graph or goal not in graph:
        return PathResult("dijkstra", False, message="Start or goal is not a graph node")
    adj = graph.adj
    distance: Dict[int, float] = {start: 0.0}
    came_from: Dict[int, int] = {}
    visited: set = set()
    heap: List[Tuple[float, int]] = [(0.0, start)]
    expanded, generated = 0, 1
    while heap:
        d_current, current = heapq.heappop(heap)
        if current in visited:
            continue                                  # stale entry (lazy deletion)
        visited.add(current)
        expanded += 1
        if current == goal:
            return PathResult("dijkstra", True, _reconstruct(came_from, goal), d_current,
                              expanded, generated, time.perf_counter() - t0,
                              message="Optimal path found")
        for neighbour, data in adj[current].items():
            if neighbour in visited:
                continue
            tentative = d_current + data[weight]      # edge relaxation
            if tentative < distance.get(neighbour, math.inf):
                distance[neighbour] = tentative
                came_from[neighbour] = current
                heapq.heappush(heap, (tentative, neighbour))
                generated += 1
    return PathResult("dijkstra", False, expanded=expanded, generated=generated,
                      runtime_s=time.perf_counter() - t0,
                      message="No path: start and goal lie in different components")


def astar_path(graph: nx.Graph, start: int, goal: int, weight: str = "weight",
               heuristic_weight: float = 1.0) -> PathResult:
    """A* search with the great-circle heuristic.

    Parameters
    ----------
    graph:
        Undirected graph; nodes carry ``lat``/``lon`` (degrees), edges the
        attribute ``weight``.
    start, goal:
        Node ids.
    weight:
        Name of the edge attribute holding the cost.
    heuristic_weight:
        1.0 keeps the heuristic admissible; larger values give weighted A*.

    Returns
    -------
    PathResult
    """
    t0 = time.perf_counter()
    if start not in graph or goal not in graph:
        return PathResult("astar", False, message="Start or goal is not a graph node")
    nodes = graph.nodes
    adj = graph.adj
    goal_lat = math.radians(nodes[goal]["lat"])
    goal_lon = math.radians(nodes[goal]["lon"])
    cos_goal = math.cos(goal_lat)
    scale = heuristic_weight * 2.0 * EARTH_RADIUS_KM
    h_cache: Dict[int, float] = {}

    def heuristic(n: int) -> float:
        """Great-circle distance from node ``n`` to the goal (haversine), km."""
        value = h_cache.get(n)
        if value is None:
            lat = math.radians(nodes[n]["lat"])
            lon = math.radians(nodes[n]["lon"])
            a = (math.sin((lat - goal_lat) * 0.5) ** 2
                 + math.cos(lat) * cos_goal * math.sin((lon - goal_lon) * 0.5) ** 2)
            value = scale * math.asin(math.sqrt(min(max(a, 0.0), 1.0)))
            h_cache[n] = value
        return value

    g_score: Dict[int, float] = {start: 0.0}
    came_from: Dict[int, int] = {}
    closed: set = set()
    heap: List[Tuple[float, float, int]] = [(heuristic(start), 0.0, start)]
    expanded, generated = 0, 1
    while heap:
        _, g_current, current = heapq.heappop(heap)
        if current in closed:
            continue                                  # stale entry (lazy deletion)
        closed.add(current)
        expanded += 1
        if current == goal:
            return PathResult("astar", True, _reconstruct(came_from, goal), g_current,
                              expanded, generated, time.perf_counter() - t0,
                              message="Optimal path found")
        for neighbour, data in adj[current].items():
            if neighbour in closed:
                continue
            tentative = g_current + data[weight]
            if tentative < g_score.get(neighbour, math.inf):
                g_score[neighbour] = tentative
                came_from[neighbour] = current
                heapq.heappush(heap, (tentative + heuristic(neighbour), tentative, neighbour))
                generated += 1
    return PathResult("astar", False, expanded=expanded, generated=generated,
                      runtime_s=time.perf_counter() - t0,
                      message="No path: start and goal lie in different components")


def path_cost(graph: nx.Graph, path: List[int], weight: str = "weight") -> Optional[float]:
    """Sum of edge costs along a node path; ``None`` if an edge is missing."""
    total = 0.0
    for a, b in zip(path[:-1], path[1:]):
        data = graph.adj[a].get(b)
        if data is None:
            return None
        total += data[weight]
    return total
