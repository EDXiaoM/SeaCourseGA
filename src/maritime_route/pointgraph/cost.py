"""Cost model shared by the genetic algorithm, Dijkstra and A*.

The cost of an edge ``e = (u, v)`` is its length increased by two penalties::

    c(e) = l(e) * (1 + alpha * s(e) + beta * phi(e))

    phi(e) = max(0, 1 - d_land(e) / r)

where

* ``l(e)`` - great-circle length of the edge, km;
* ``s(e)`` - share of the edge in coastal (shallow) water, 0 / 0.5 / 1;
* ``d_land(e)`` - distance from the edge to the nearest land point, km;
* ``r`` - radius of the danger zone around land, km;
* ``alpha`` - coastal-water penalty, ``beta`` - danger-zone penalty.

``phi`` is 1 for an edge that touches land and falls linearly to 0 at the
edge of the danger zone. The cost of a route is the sum of its edge costs,
which splits into the three terms used as the fitness of the genetic
algorithm::

    F(P) = L(P) + alpha * L_c(P) + beta * L_d(P)

with the route length ``L``, the length sailed in coastal water ``L_c`` and
the danger-weighted length ``L_d``. Because every factor is at least 1, the
cost of an edge is never smaller than its length, which keeps the great-circle
heuristic of A* admissible.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Dict, List

import networkx as nx

from .graph import SeaGraph


@dataclass(frozen=True)
class CostWeights:
    """Penalty weights of the cost model.

    Attributes
    ----------
    coastal_penalty:
        ``alpha`` - extra cost per km sailed in coastal water (0.5 = +50 %).
    danger_penalty:
        ``beta`` - extra cost per km sailed directly next to land.
    danger_radius_km:
        ``r`` - width of the danger zone around land points, km.
    """

    coastal_penalty: float = 0.5
    danger_penalty: float = 2.0
    danger_radius_km: float = 10.0

    def to_dict(self) -> Dict:
        return asdict(self)


def danger_factor(land_km: float, radius_km: float) -> float:
    """``phi`` - 1 at the shore, 0 outside the danger zone."""
    if radius_km <= 0 or not math.isfinite(land_km):
        return 0.0
    return max(0.0, 1.0 - land_km / radius_km)


def edge_cost(length: float, coastal: float, land_km: float, weights: CostWeights) -> float:
    """Cost ``c(e)`` of one edge (weighted km)."""
    phi = danger_factor(land_km, weights.danger_radius_km)
    return length * (1.0 + weights.coastal_penalty * coastal + weights.danger_penalty * phi)


def apply_costs(sea: SeaGraph, weights: CostWeights) -> None:
    """Write the attribute ``weight`` (edge cost) on every edge of the graph."""
    for _, _, data in sea.graph.edges(data=True):
        data["weight"] = edge_cost(data["length"], data["coastal"], data["land_km"], weights)


def route_breakdown(graph: nx.Graph, path: List[int], weights: CostWeights) -> Dict[str, float]:
    """Terms of the fitness function for a node path.

    Returns
    -------
    dict
        ``length_km`` (L), ``coastal_km`` (L_c), ``danger_km`` (L_d),
        ``cost`` (F) and ``min_land_km`` (closest approach to land).
    """
    length = coastal = danger = 0.0
    min_land = math.inf
    for a, b in zip(path[:-1], path[1:]):
        data = graph.edges[a, b]
        length += data["length"]
        coastal += data["length"] * data["coastal"]
        danger += data["length"] * danger_factor(data["land_km"], weights.danger_radius_km)
        min_land = min(min_land, data["land_km"])
    cost = length + weights.coastal_penalty * coastal + weights.danger_penalty * danger
    return {"length_km": length, "coastal_km": coastal, "danger_km": danger,
            "cost": cost, "min_land_km": min_land}
