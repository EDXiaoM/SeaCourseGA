"""Genetic algorithm for the ship-course problem on the point graph.

Encoding
--------
A chromosome is a route: the sequence of graph nodes ``[s, v1, ..., vk, t]``
from the departure ``s`` to the destination ``t`` in which every two
consecutive nodes are joined by an edge and no node occurs twice. The length
of the chromosome is variable. This path encoding follows Ahn and
Ramakrishna (2002); every chromosome is a feasible route by construction, so
the fitness never has to judge a broken route.

Fitness
-------
The fitness to be minimised is the route cost of :mod:`.cost`::

    F(P) = L(P) + alpha * L_c(P) + beta * L_d(P)

Operators
---------
* **Initialisation** - every individual is grown by a randomised depth-first
  walk from ``s`` towards ``t``. At each step the next node is drawn among the
  unvisited neighbours with probability proportional to
  ``exp(kappa * g)``, where ``g`` is the progress towards the goal divided by
  the cost of the edge. ``kappa`` is drawn anew for each walk, so the initial
  population mixes almost straight routes with strongly meandering ones. A
  dead end is left by backtracking. In ``via_share`` of the cases the walk is
  first led to a random intermediate node drawn in a circle around the
  midpoint of its end nodes, which spreads the population over different
  corridors (for example inshore and offshore of a cape).
* **Selection** - tournament selection.
* **Crossover** - one-point crossover at a common node: both parents are cut
  at a node they share and the head of one parent is joined to the tail of the
  other. Loops that may appear are removed.
* **Mutation** - one of two moves:
  *re-routing* replaces the part of the route between two random positions by
  a new random walk (possibly through an intermediate node) between the same
  nodes; *shortcut* replaces a sub-route
  ``v_i ... v_j`` by the direct edge ``(v_i, v_j)`` when that edge exists and
  is cheaper.
* **Elitism** - the best individuals pass unchanged to the next generation,
  so the best cost never increases.
* **Termination** - after the given number of generations, after
  ``stagnation_limit`` generations without improvement, or on a stop request
  from the user interface.

All random numbers come from one ``random.Random`` seeded with
``GAConfig.seed``, so a run is reproducible.
"""
from __future__ import annotations

import math
import random
import statistics
import time
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import networkx as nx
import numpy as np
from scipy.spatial import cKDTree

from ..config import EARTH_RADIUS_KM
from .search import PathResult

Route = List[int]
#: ``progress(generation, best_cost, median_cost)``.
GAProgress = Optional[Callable[[int, float, float], None]]
#: Returns True when the user asked to stop the run.
StopFlag = Optional[Callable[[], bool]]


@dataclass(frozen=True)
class GAConfig:
    """Parameters of the genetic algorithm (all editable in the GUI).

    Attributes
    ----------
    population_size:
        Number of routes in a generation.
    generations:
        Maximal number of generations.
    crossover_rate:
        Probability that two selected parents are recombined.
    mutation_rate:
        Probability that a child is mutated.
    tournament_size:
        Number of individuals compared in one tournament.
    elite:
        Number of best individuals copied unchanged.
    stagnation_limit:
        Stop after this many generations without improvement (0 = never).
    shortcut_share:
        Share of mutations that are shortcuts (the rest are re-routings).
    reroute_window:
        Largest number of route positions replaced by one re-routing.
    kappa_range:
        Range of the goal-attraction coefficient of the random walk.
    via_share:
        Share of random walks (initial routes and re-routings) that are led
        through a random intermediate node.
    via_spread:
        Range of the radius of the circle in which the intermediate node is
        drawn, as a fraction of the distance between the two end nodes.
    seed:
        Seed of the random generator.
    """

    population_size: int = 100
    generations: int = 300
    crossover_rate: float = 0.8
    mutation_rate: float = 0.3
    tournament_size: int = 3
    elite: int = 2
    stagnation_limit: int = 80
    shortcut_share: float = 0.4
    reroute_window: int = 60
    kappa_range: Tuple[float, float] = (1.0, 15.0)
    via_share: float = 0.5
    via_spread: Tuple[float, float] = (0.1, 0.5)
    seed: int = 42

    def to_dict(self) -> Dict:
        return asdict(self)


class _RouteSpace:
    """Adjacency, costs and geometry of the graph in plain Python containers.

    NetworkX attribute look-ups are convenient but slow inside the inner loop
    of the algorithm, so the graph is copied once into dictionaries.
    """

    def __init__(self, graph: nx.Graph, weight: str = "weight") -> None:
        self.cost: Dict[int, Dict[int, float]] = {}
        self.length: Dict[int, Dict[int, float]] = {}
        for u, nbrs in graph.adj.items():
            self.cost[u] = {v: d[weight] for v, d in nbrs.items()}
            self.length[u] = {v: d["length"] for v, d in nbrs.items()}
        self.lat = {n: math.radians(d["lat"]) for n, d in graph.nodes(data=True)}
        self.lon = {n: math.radians(d["lon"]) for n, d in graph.nodes(data=True)}
        # Spatial index of the nodes, used to draw random intermediate nodes.
        self.nodes = list(graph.nodes)
        lat = np.radians([graph.nodes[n]["lat"] for n in self.nodes])
        lon = np.radians([graph.nodes[n]["lon"] for n in self.nodes])
        self.xyz = EARTH_RADIUS_KM * np.column_stack(
            (np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)))
        self.position = {n: i for i, n in enumerate(self.nodes)}
        self.tree = cKDTree(self.xyz)
        self.evaluations = 0

    def distance(self, a: int, b: int) -> float:
        """Great-circle distance between two nodes, km (haversine)."""
        la, lb = self.lat[a], self.lat[b]
        h = (math.sin((lb - la) * 0.5) ** 2
             + math.cos(la) * math.cos(lb) * math.sin((self.lon[b] - self.lon[a]) * 0.5) ** 2)
        return 2.0 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(max(h, 0.0), 1.0)))

    def route_cost(self, route: Sequence[int]) -> float:
        """Fitness ``F`` of a route (sum of edge costs)."""
        self.evaluations += 1
        cost = self.cost
        return sum(cost[a][b] for a, b in zip(route[:-1], route[1:]))

    def walk(self, src: int, dst: int, rng: random.Random, kappa: float,
             forbidden: Optional[set] = None, max_steps: Optional[int] = None) -> Optional[Route]:
        """Randomised depth-first walk from ``src`` to ``dst``.

        Parameters
        ----------
        src, dst:
            End nodes.
        rng:
            Random generator.
        kappa:
            Goal attraction; 0 gives a uniform random walk.
        forbidden:
            Nodes the walk must not enter (the rest of the route).
        max_steps:
            Upper bound on the number of forward steps (``None`` = unbounded;
            the walk then ends at the latest when the component is exhausted).

        Returns
        -------
        list of int or None
            A simple path ``[src, ..., dst]`` or ``None`` if none was found.
        """
        visited = set(forbidden or ())
        visited.discard(dst)
        visited.add(src)
        stack = [src]
        h_cache: Dict[int, float] = {}

        def h(n: int) -> float:
            value = h_cache.get(n)
            if value is None:
                value = self.distance(n, dst)
                h_cache[n] = value
            return value

        steps = 0
        while stack:
            u = stack[-1]
            if u == dst:
                return stack
            if max_steps is not None and steps >= max_steps:
                return None
            options = [v for v in self.cost[u] if v not in visited]
            if not options:
                stack.pop()                           # dead end: backtrack
                continue
            if dst in options:
                v = dst
            else:
                hu = h(u)
                weights = []
                for v in options:
                    edge = self.cost[u][v] or 1e-9
                    gain = (hu - h(v)) / edge         # progress per unit of cost
                    weights.append(math.exp(kappa * gain))
                v = rng.choices(options, weights=weights, k=1)[0]
            visited.add(v)
            stack.append(v)
            steps += 1
        return None


    def random_via(self, a: int, b: int, rng: random.Random, spread: float,
                   forbidden: set) -> Optional[int]:
        """Random node inside a circle around the midpoint of ``a`` and ``b``.

        The radius is ``spread`` times the distance between the two nodes
        (at least 5 km), so the drawn node can pull a route far to the side
        of the direct line.
        """
        pa, pb = self.xyz[self.position[a]], self.xyz[self.position[b]]
        radius = max(spread * float(np.linalg.norm(pb - pa)), 5.0)
        candidates = self.tree.query_ball_point(0.5 * (pa + pb), radius)
        candidates = [self.nodes[i] for i in candidates]
        candidates = [n for n in candidates if n not in forbidden and n != a and n != b]
        if not candidates:
            return None
        return rng.choice(candidates)

    def via_walk(self, src: int, dst: int, rng: random.Random, kappa: float, spread: float,
                 forbidden: Optional[set] = None, max_steps: Optional[int] = None) -> Optional[Route]:
        """Walk ``src -> via -> dst`` through a random intermediate node."""
        forbidden = set(forbidden or ())
        via = self.random_via(src, dst, rng, spread, forbidden)
        if via is None:
            return self.walk(src, dst, rng, kappa, forbidden, max_steps)
        first = self.walk(src, via, rng, kappa, forbidden | {dst}, max_steps)
        if first is None:
            return None
        second = self.walk(via, dst, rng, kappa, forbidden | set(first[:-1]), max_steps)
        if second is None:
            return None
        return first + second[1:]


def _remove_loops(route: Route) -> Route:
    """Cut out every cycle so that each node occurs at most once."""
    out: Route = []
    position: Dict[int, int] = {}
    for node in route:
        if node in position:
            cut = position[node]
            for removed in out[cut + 1:]:
                del position[removed]
            del out[cut + 1:]
        else:
            position[node] = len(out)
            out.append(node)
    return out


def genetic_path(graph: nx.Graph, start: int, goal: int, config: GAConfig = GAConfig(),
                 weight: str = "weight", progress: GAProgress = None,
                 should_stop: StopFlag = None) -> PathResult:
    """Search a low-cost route with the genetic algorithm.

    Parameters
    ----------
    graph:
        Navigation graph with edge attributes ``weight`` and ``length`` and
        node attributes ``lat``/``lon``.
    start, goal:
        Node ids of the departure and the destination.
    config:
        Parameters of the algorithm.
    weight:
        Edge attribute holding the cost.
    progress:
        Optional callback ``progress(generation, best, median)``.
    should_stop:
        Optional callback; when it returns True the run ends after the
        current generation.

    Returns
    -------
    PathResult
        ``expanded`` = number of fitness evaluations, ``generated`` = number
        of generations run, ``best_history``/``median_history`` = convergence
        curves (index 0 = initial population).
    """
    t0 = time.perf_counter()
    if start not in graph or goal not in graph:
        return PathResult("genetic", False, message="Start or goal is not a graph node")
    if start == goal:
        return PathResult("genetic", True, [start], 0.0, runtime_s=time.perf_counter() - t0,
                          message="Start and goal coincide")
    if not nx.has_path(graph, start, goal):
        return PathResult("genetic", False, runtime_s=time.perf_counter() - t0,
                          message="No path: start and goal lie in different components")

    rng = random.Random(config.seed)
    space = _RouteSpace(graph, weight)
    k_lo, k_hi = config.kappa_range
    s_lo, s_hi = config.via_spread

    def random_route(src: int, dst: int, forbidden: Optional[set] = None,
                     max_steps: Optional[int] = None) -> Optional[Route]:
        """Random walk, led through an intermediate node in ``via_share`` of cases."""
        kappa = rng.uniform(k_lo, k_hi)
        if rng.random() < config.via_share:
            return space.via_walk(src, dst, rng, kappa, rng.uniform(s_lo, s_hi),
                                  forbidden, max_steps)
        return space.walk(src, dst, rng, kappa, forbidden, max_steps)

    # ---- initial population ------------------------------------------------
    population: List[Route] = []
    attempts = 0
    while len(population) < config.population_size and attempts < 5 * config.population_size:
        attempts += 1
        route = random_route(start, goal)
        if route is not None:
            population.append(route)
    if not population:
        return PathResult("genetic", False, runtime_s=time.perf_counter() - t0,
                          message="Could not create an initial population")
    while len(population) < config.population_size:
        population.append(list(rng.choice(population)))
    fitness = [space.route_cost(r) for r in population]

    # ---- operators -----------------------------------------------------------
    def tournament() -> Route:
        contenders = rng.sample(range(len(population)), min(config.tournament_size, len(population)))
        return population[min(contenders, key=lambda i: fitness[i])]

    def crossover(a: Route, b: Route) -> Tuple[Route, Route]:
        common = list(set(a[1:-1]) & set(b[1:-1]))
        if not common:
            return list(a), list(b)
        node = rng.choice(common)
        i, j = a.index(node), b.index(node)
        return _remove_loops(a[:i] + b[j:]), _remove_loops(b[:j] + a[i:])

    def reroute(route: Route) -> Route:
        if len(route) < 3:
            return route
        span = rng.randint(2, max(2, min(config.reroute_window, len(route) - 1)))
        i = rng.randrange(0, len(route) - span)
        j = i + span
        forbidden = set(route[:i]) | set(route[j + 1:])
        sub = random_route(route[i], route[j], forbidden, max_steps=8 * span + 40)
        if sub is None:
            return route
        return route[:i] + sub + route[j + 1:]

    def shortcut(route: Route) -> Route:
        if len(route) < 3:
            return route
        i = rng.randrange(0, len(route) - 2)
        adj = space.cost[route[i]]
        for j in range(min(len(route) - 1, i + config.reroute_window), i + 1, -1):
            if route[j] in adj:
                old = sum(space.cost[a][b] for a, b in zip(route[i:j], route[i + 1:j + 1]))
                if adj[route[j]] < old:
                    return route[:i + 1] + route[j:]
                break
        return route

    def mutate(route: Route) -> Route:
        if rng.random() < config.shortcut_share:
            return shortcut(route)
        return reroute(route)

    # ---- evolution -------------------------------------------------------------
    best_i = min(range(len(population)), key=lambda i: fitness[i])
    best, best_fit = list(population[best_i]), fitness[best_i]
    best_history = [best_fit]
    median_history = [statistics.median(fitness)]
    stagnant = 0
    generation = 0
    stopped = False
    for generation in range(1, config.generations + 1):
        order = sorted(range(len(population)), key=lambda i: fitness[i])
        offspring: List[Route] = [list(population[i]) for i in order[:config.elite]]
        while len(offspring) < config.population_size:
            a, b = tournament(), tournament()
            if rng.random() < config.crossover_rate:
                children = crossover(a, b)
            else:
                children = (list(a), list(b))
            for child in children:
                if rng.random() < config.mutation_rate:
                    child = mutate(child)
                offspring.append(child)
                if len(offspring) == config.population_size:
                    break
        population = offspring
        fitness = [space.route_cost(r) for r in population]
        gen_best = min(range(len(population)), key=lambda i: fitness[i])
        if fitness[gen_best] < best_fit - 1e-9:
            best, best_fit = list(population[gen_best]), fitness[gen_best]
            stagnant = 0
        else:
            stagnant += 1
        best_history.append(best_fit)
        median_history.append(statistics.median(fitness))
        if progress is not None:
            progress(generation, best_fit, median_history[-1])
        if should_stop is not None and should_stop():
            stopped = True
            break
        if config.stagnation_limit and stagnant >= config.stagnation_limit:
            break

    reason = ("stopped by the user" if stopped else
              "no improvement" if config.stagnation_limit and stagnant >= config.stagnation_limit
              else "generation limit")
    return PathResult(
        algorithm="genetic", found=True, path=best, cost=best_fit,
        expanded=space.evaluations, generated=generation,
        runtime_s=time.perf_counter() - t0,
        best_history=best_history, median_history=median_history,
        message=f"Best route after {generation} generations ({reason}), {len(best)} nodes",
    )
