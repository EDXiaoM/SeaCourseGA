"""Navigation graph built directly on the labelled water points.

Nodes
-----
Every OPEN_SEA or COASTAL_SEA point inside the area of interest becomes a
node. Land points (NEAR_COAST, COASTLINE) never become nodes; they are the
obstacles of the problem.

Edges
-----
Candidate edges join each node with its ``k`` nearest water neighbours that
lie closer than ``max_edge_km``. Two construction modes are offered:

* ``"distance"`` - every candidate edge is kept. The graph is purely
  geometric; an edge may pass over a narrow cape or island, which is then only
  discouraged by the danger penalty of the cost model.
* ``"visibility"`` - a candidate edge is kept only if the segment between its
  end points "sees" no land. The segment is sampled every ``sample_step_km``
  kilometres and every sample is labelled with the class of its nearest
  dataset point (1-nearest-neighbour rule, i.e. the labelled points split the
  plane into Voronoi cells). If any sample falls into the cell of a land
  point, the edge crosses land and is discarded.

For every edge three attributes are stored, so that the costs can be
recomputed for new penalty weights without rebuilding the graph:

* ``length`` - great-circle length, km;
* ``coastal`` - share of the edge in coastal water, 0, 0.5 or 1 (mean of the
  two end-point flags);
* ``land_km`` - distance from the segment to the nearest land point, km
  (``inf`` when no land point is within the search radius).

Geometry
--------
Points are converted to 3-D Cartesian coordinates on a sphere of radius
6371.0088 km. A k-d tree on these coordinates returns neighbours in exact
great-circle order, because the chord length ``2R sin(d / 2R)`` grows
monotonically with the arc length ``d``. The point-to-segment distance is
computed in the same 3-D space; for segments of a few tens of kilometres the
difference between the chord and the arc is below 0.01 %.
"""
from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
from scipy.spatial import cKDTree

from ..config import EARTH_RADIUS_KM
from ..routing.geodesy import haversine_km
from .dataset import LAND_INDICES, WATER_INDICES, BBox, PointSet

#: ``progress(message, fraction)`` callback used by the GUI.
ProgressFn = Optional[Callable[[str, float], None]]


@dataclass(frozen=True)
class GraphConfig:
    """Parameters of graph construction.

    Attributes
    ----------
    mode:
        ``"distance"`` or ``"visibility"`` (see the module docstring).
    k_neighbours:
        Number of nearest water neighbours tested for every node.
    max_edge_km:
        Longest admissible edge, km.
    sample_step_km:
        Visibility mode: spacing of the test samples along an edge, km.
    land_search_km:
        Edge-to-land distances are computed up to this value; farther land is
        recorded as ``inf``. It must not be smaller than the danger radius of
        the cost model (the GUI limits the radius accordingly).
    margin_deg:
        Margin added around the area of interest when land points are
        collected, so that obstacles just outside the area are respected.
    """

    mode: str = "visibility"
    k_neighbours: int = 10
    max_edge_km: float = 40.0
    sample_step_km: float = 1.0
    land_search_km: float = 30.0
    margin_deg: float = 0.5

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class GraphStats:
    """Summary of a built graph, shown in the GUI and written to the log."""

    n_water_points: int
    n_land_points: int
    n_candidate_edges: int
    n_edges: int
    n_removed_by_visibility: int
    n_components: int
    largest_component: int
    mean_degree: float
    mean_edge_km: float
    seconds: float

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SeaGraph:
    """The navigation graph and the arrays it was built from.

    Attributes
    ----------
    graph:
        Undirected :class:`networkx.Graph`; node ids are ``0..n-1``; node
        attributes ``lat``, ``lon``, ``cls``; edge attributes ``length``,
        ``coastal``, ``land_km`` and, after
        :func:`~maritime_route.pointgraph.cost.apply_costs`, ``weight``.
    lat, lon, cls:
        Node coordinates (degrees) and classes, indexed by node id.
    land_lat, land_lon:
        Land points of the area, used for drawing and by the tests.
    bbox:
        Area of interest.
    config:
        Construction parameters.
    stats:
        Summary numbers.
    component:
        Connected-component label of every node (0 = largest component).
    """

    graph: nx.Graph
    lat: np.ndarray
    lon: np.ndarray
    cls: np.ndarray
    land_lat: np.ndarray
    land_lon: np.ndarray
    bbox: BBox
    config: GraphConfig
    stats: GraphStats
    component: np.ndarray
    _tree: Optional[cKDTree] = None

    @property
    def n_nodes(self) -> int:
        return int(self.lat.shape[0])

    def coords(self, path: List[int]) -> List[Tuple[float, float]]:
        """``(lat, lon)`` of the nodes of a path."""
        return [(float(self.lat[i]), float(self.lon[i])) for i in path]

    def nearest_node(self, lat: float, lon: float,
                     largest_only: bool = False) -> Tuple[int, float]:
        """Node closest to a position and its great-circle distance (km).

        Parameters
        ----------
        lat, lon:
            Position, degrees.
        largest_only:
            Restrict the search to the largest connected component.
        """
        if self._tree is None:
            self._tree = cKDTree(to_xyz(self.lat, self.lon))
        query = to_xyz(np.array([lat]), np.array([lon]))[0]
        if not largest_only:
            _, idx = self._tree.query(query)
        else:
            k = min(self.n_nodes, 64)
            while True:
                _, cand = self._tree.query(query, k=k)
                cand = np.atleast_1d(cand)
                hit = cand[self.component[cand] == 0]
                if hit.size or k >= self.n_nodes:
                    idx = int(hit[0]) if hit.size else int(cand[0])
                    break
                k = min(self.n_nodes, k * 4)
        idx = int(idx)
        return idx, float(haversine_km(lat, lon, self.lat[idx], self.lon[idx]))


def to_xyz(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Cartesian coordinates (km) of points on the sphere of radius R."""
    phi = np.radians(np.asarray(lat, dtype=np.float64))
    lam = np.radians(np.asarray(lon, dtype=np.float64))
    cos_phi = np.cos(phi)
    return EARTH_RADIUS_KM * np.column_stack((cos_phi * np.cos(lam), cos_phi * np.sin(lam), np.sin(phi)))


def chord_from_arc(arc_km: float) -> float:
    """Chord length that corresponds to a great-circle distance (km)."""
    return 2.0 * EARTH_RADIUS_KM * math.sin(min(arc_km, math.pi * EARTH_RADIUS_KM) / (2.0 * EARTH_RADIUS_KM))


def segment_land_distance(a: np.ndarray, b: np.ndarray, land_xyz: np.ndarray,
                          land_tree: Optional[cKDTree], search_km: float,
                          chunk: int = 20000) -> np.ndarray:
    """Distance from every segment ``a[i] - b[i]`` to the nearest land point.

    Only land points within ``half length + search_km`` of the segment
    midpoint are examined; when there is none the distance is ``inf``.

    Parameters
    ----------
    a, b:
        ``(m, 3)`` Cartesian end points of the segments, km.
    land_xyz:
        ``(p, 3)`` Cartesian land points, km.
    land_tree:
        k-d tree of ``land_xyz`` (``None`` when there are no land points).
    search_km:
        Extra search radius around each segment.
    chunk:
        Number of segments processed per vectorised batch.

    Returns
    -------
    numpy.ndarray
        ``(m,)`` distances in km.
    """
    m = a.shape[0]
    out = np.full(m, np.inf)
    if land_tree is None or m == 0:
        return out
    for s in range(0, m, chunk):
        e = min(m, s + chunk)
        aa, bb = a[s:e], b[s:e]
        mid = 0.5 * (aa + bb)
        radius = 0.5 * np.linalg.norm(bb - aa, axis=1) + search_km
        hits = land_tree.query_ball_point(mid, radius)
        counts = np.fromiter((len(h) for h in hits), dtype=np.int64, count=e - s)
        if counts.sum() == 0:
            continue
        seg = np.repeat(np.arange(e - s), counts)
        pts = np.concatenate([np.asarray(h, dtype=np.int64) for h in hits if len(h)])
        p = land_xyz[pts]
        ab = (bb - aa)[seg]
        ap = p - aa[seg]
        denom = np.einsum("ij,ij->i", ab, ab)
        t = np.where(denom > 0, np.einsum("ij,ij->i", ap, ab) / np.where(denom > 0, denom, 1.0), 0.0)
        t = np.clip(t, 0.0, 1.0)
        closest = aa[seg] + ab * t[:, None]
        dist = np.linalg.norm(p - closest, axis=1)
        best = np.full(e - s, np.inf)
        np.minimum.at(best, seg, dist)
        out[s:e] = best
    return out


def segment_visible(a: np.ndarray, b: np.ndarray, length: np.ndarray,
                    water_xyz: np.ndarray, land_xyz: np.ndarray, step_km: float,
                    chunk: int = 200000) -> np.ndarray:
    """Line-of-sight test of segments over the labelled point map.

    Interior samples are placed every ``step_km`` along each segment; a sample
    is "land" when its nearest labelled point (water or land) is a land point.
    A segment is visible when none of its samples is land.

    Parameters
    ----------
    a, b:
        ``(m, 3)`` Cartesian end points, km.
    length:
        ``(m,)`` segment lengths, km.
    water_xyz, land_xyz:
        Cartesian coordinates of the water and land points, km.
    step_km:
        Sampling step, km.
    chunk:
        Number of samples classified per batch.

    Returns
    -------
    numpy.ndarray of bool
        ``(m,)``, True for a segment that does not cross land.
    """
    m = a.shape[0]
    visible = np.ones(m, dtype=bool)
    if m == 0 or land_xyz.shape[0] == 0:
        return visible
    tree = cKDTree(np.vstack((water_xyz, land_xyz)))
    n_water = water_xyz.shape[0]
    n_samples = np.maximum(np.ceil(length / max(step_km, 1e-3)).astype(np.int64) - 1, 1)
    seg = np.repeat(np.arange(m), n_samples)
    # Position of every sample inside its segment: k / (n + 1), k = 1..n.
    first = np.cumsum(n_samples) - n_samples
    k = np.arange(seg.size) - np.repeat(first, n_samples) + 1
    t = k / (np.repeat(n_samples, n_samples) + 1.0)
    for s in range(0, seg.size, chunk):
        e = min(seg.size, s + chunk)
        idx_seg = seg[s:e]
        pts = a[idx_seg] + (b[idx_seg] - a[idx_seg]) * t[s:e, None]
        _, nearest = tree.query(pts)
        on_land = nearest >= n_water
        visible[idx_seg[on_land]] = False
    return visible


def build_graph(points: PointSet, bbox: BBox, config: GraphConfig = GraphConfig(),
                progress: ProgressFn = None) -> SeaGraph:
    """Build the navigation graph of an area.

    Parameters
    ----------
    points:
        Whole labelled dataset.
    bbox:
        Area of interest ``(lat_min, lat_max, lon_min, lon_max)``.
    config:
        Construction parameters.
    progress:
        Optional ``progress(message, fraction)`` callback.

    Returns
    -------
    SeaGraph

    Raises
    ------
    ValueError
        If the area contains fewer than two water points or the mode is unknown.
    """
    if config.mode not in ("distance", "visibility"):
        raise ValueError(f"Unknown graph mode: {config.mode}")
    t0 = time.perf_counter()

    def report(message: str, fraction: float) -> None:
        if progress is not None:
            progress(message, fraction)

    inside = points.in_bbox(bbox)
    water_mask = inside & np.isin(points.cls, WATER_INDICES)
    land_mask = points.in_bbox(bbox, config.margin_deg) & np.isin(points.cls, LAND_INDICES)
    lat, lon, cls = points.lat[water_mask], points.lon[water_mask], points.cls[water_mask]
    land_lat, land_lon = points.lat[land_mask], points.lon[land_mask]
    n = lat.shape[0]
    if n < 2:
        raise ValueError("The selected area contains fewer than two water points")
    report(f"{n} water points, {land_lat.shape[0]} land points", 0.05)

    # 1. Candidate edges: k nearest neighbours within max_edge_km.
    xyz = to_xyz(lat, lon)
    tree = cKDTree(xyz)
    k = min(config.k_neighbours + 1, n)
    dist, idx = tree.query(xyz, k=k, distance_upper_bound=chord_from_arc(config.max_edge_km))
    rows = np.repeat(np.arange(n), k - 1)
    cols = idx[:, 1:].ravel()
    ok = cols < n                       # missing neighbours are reported as index n
    rows, cols = rows[ok], cols[ok]
    lo, hi = np.minimum(rows, cols), np.maximum(rows, cols)
    pairs = np.unique(np.column_stack((lo, hi)), axis=0)
    pairs = pairs[pairs[:, 0] != pairs[:, 1]]
    n_candidates = int(pairs.shape[0])
    report(f"{n_candidates} candidate edges", 0.25)

    # 2. Edge attributes.
    u, v = pairs[:, 0], pairs[:, 1]
    length = haversine_km(lat[u], lon[u], lat[v], lon[v])
    coastal_flag = (cls == WATER_INDICES[1]).astype(np.float64)
    coastal = 0.5 * (coastal_flag[u] + coastal_flag[v])
    land_xyz = to_xyz(land_lat, land_lon) if land_lat.size else np.zeros((0, 3))
    land_tree = cKDTree(land_xyz) if land_lat.size else None
    search = config.land_search_km
    land_km = segment_land_distance(xyz[u], xyz[v], land_xyz, land_tree, search)
    report("Distances to land computed", 0.75)

    # 3. Visibility filter.
    keep = np.ones(n_candidates, dtype=bool)
    if config.mode == "visibility" and land_lat.size:
        keep = segment_visible(xyz[u], xyz[v], length, xyz, land_xyz, config.sample_step_km)
    removed = int((~keep).sum())

    graph = nx.Graph()
    graph.add_nodes_from(
        (i, {"lat": float(lat[i]), "lon": float(lon[i]), "cls": int(cls[i])}) for i in range(n)
    )
    graph.add_edges_from(
        (int(a), int(b), {"length": float(d), "coastal": float(c), "land_km": float(l)})
        for a, b, d, c, l in zip(u[keep], v[keep], length[keep], coastal[keep], land_km[keep])
    )

    # 4. Connected components, label 0 = largest.
    components = sorted(nx.connected_components(graph), key=len, reverse=True)
    component = np.empty(n, dtype=np.int64)
    for label, nodes in enumerate(components):
        component[list(nodes)] = label
    n_edges = graph.number_of_edges()
    stats = GraphStats(
        n_water_points=n, n_land_points=int(land_lat.shape[0]),
        n_candidate_edges=n_candidates, n_edges=n_edges,
        n_removed_by_visibility=removed, n_components=len(components),
        largest_component=len(components[0]) if components else 0,
        mean_degree=2.0 * n_edges / n,
        mean_edge_km=float(length[keep].mean()) if n_edges else 0.0,
        seconds=time.perf_counter() - t0,
    )
    report("Graph ready", 1.0)
    return SeaGraph(graph=graph, lat=lat, lon=lon, cls=cls, land_lat=land_lat,
                    land_lon=land_lon, bbox=bbox, config=config, stats=stats,
                    component=component, _tree=tree)
