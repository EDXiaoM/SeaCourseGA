"""Tests of the point-graph route search of the course project.

A small synthetic dataset is used: a regular field of water points with a
vertical strip of land points in the middle that has one gap (a strait). The
expected behaviour is known exactly for this layout.
"""
from __future__ import annotations

import json
import math
import random

import networkx as nx
import numpy as np
import pytest

from maritime_route.pointgraph.cost import CostWeights, apply_costs, danger_factor, edge_cost, route_breakdown
from maritime_route.pointgraph.dataset import PointSet, load_points
from maritime_route.pointgraph.genetic import GAConfig, _remove_loops, genetic_path
from maritime_route.pointgraph.graph import GraphConfig, build_graph, to_xyz
from maritime_route.pointgraph.search import astar_path, dijkstra_path, path_cost
from maritime_route.pointgraph.session import VOYAGES, CourseSession, route_area

STEP = 0.05          # degrees between grid points (about 5.5 km)
BBOX = (0.0, 1.0, 0.0, 1.0)


def _strait_points() -> PointSet:
    """Water field 0..1 deg with a land wall at lon 0.5 and a gap at lat 0.8-0.9."""
    lat, lon, cls = [], [], []
    for i in range(21):
        for j in range(21):
            y, x = i * STEP, j * STEP
            if abs(x - 0.5) < 1e-9 and not (0.79 < y < 0.91):
                lat.append(y); lon.append(x); cls.append(2)       # land wall
            else:
                coastal = abs(x - 0.5) < 0.11
                lat.append(y); lon.append(x); cls.append(1 if coastal else 0)
    # densify the wall so that no water edge can slip between two land points
    for y in np.arange(0.0, 0.8, STEP / 4):
        lat.append(float(y)); lon.append(0.5); cls.append(3)
    n = len(lat)
    return PointSet(np.array(lat), np.array(lon), np.array(cls, dtype=np.int8),
                    np.array(["test"] * n, dtype=object))


@pytest.fixture(scope="module")
def points() -> PointSet:
    return _strait_points()


@pytest.fixture(scope="module")
def sea(points):
    sea = build_graph(points, BBOX, GraphConfig(mode="visibility", k_neighbours=8, max_edge_km=12))
    apply_costs(sea, CostWeights())
    return sea


def _node(sea, lat, lon):
    return sea.nearest_node(lat, lon)[0]


def test_xyz_is_on_the_sphere():
    xyz = to_xyz(np.array([0.0, 45.0, -90.0]), np.array([0.0, 10.0, 0.0]))
    assert np.allclose(np.linalg.norm(xyz, axis=1), 6371.0088)


def test_land_points_are_not_nodes(sea):
    assert set(np.unique(sea.cls)) <= {0, 1}
    assert sea.n_nodes == sea.graph.number_of_nodes()


def test_visibility_removes_edges_across_the_wall(points, sea):
    by_distance = build_graph(points, BBOX, GraphConfig(mode="distance", k_neighbours=8, max_edge_km=12))
    assert by_distance.stats.n_removed_by_visibility == 0
    assert sea.stats.n_removed_by_visibility > 0
    # In the visibility graph no edge joins the two sides south of the strait.
    for u, v in sea.graph.edges():
        lon_u, lon_v = sea.lon[u], sea.lon[v]
        if (lon_u - 0.5) * (lon_v - 0.5) < 0:
            assert 0.75 < min(sea.lat[u], sea.lat[v]) and max(sea.lat[u], sea.lat[v]) < 0.95


def test_edge_attributes(sea):
    for _, _, d in sea.graph.edges(data=True):
        assert d["length"] > 0
        assert d["coastal"] in (0.0, 0.5, 1.0)
        assert d["weight"] >= d["length"] - 1e-9          # penalties never reduce the cost


def test_cost_model():
    w = CostWeights(coastal_penalty=0.5, danger_penalty=2.0, danger_radius_km=10.0)
    assert danger_factor(0.0, 10.0) == 1.0
    assert danger_factor(5.0, 10.0) == pytest.approx(0.5)
    assert danger_factor(12.0, 10.0) == 0.0
    assert danger_factor(math.inf, 10.0) == 0.0
    assert edge_cost(10.0, 1.0, 5.0, w) == pytest.approx(10.0 * (1 + 0.5 + 1.0))


def test_dijkstra_and_astar_match_networkx(sea):
    s, g = _node(sea, 0.1, 0.1), _node(sea, 0.1, 0.9)
    d = dijkstra_path(sea.graph, s, g)
    a = astar_path(sea.graph, s, g)
    reference = nx.dijkstra_path_length(sea.graph, s, g, weight="weight")
    assert d.found and a.found
    assert d.cost == pytest.approx(reference)
    assert a.cost == pytest.approx(reference)
    assert a.expanded <= d.expanded
    assert path_cost(sea.graph, d.path) == pytest.approx(d.cost)
    # The only way across leads through the strait in the north.
    assert max(sea.lat[d.path]) > 0.79


def test_unreachable_goal_is_reported():
    g = nx.Graph()
    g.add_node(0, lat=0.0, lon=0.0); g.add_node(1, lat=0.0, lon=1.0)
    assert not dijkstra_path(g, 0, 1, weight="weight").found
    assert not astar_path(g, 0, 1, weight="weight").found
    assert not genetic_path(g, 0, 1).found


def test_remove_loops():
    assert _remove_loops([1, 2, 3, 2, 4]) == [1, 2, 4]
    assert _remove_loops([1, 2, 3, 4, 1, 5]) == [1, 5]
    assert _remove_loops([1, 2, 3]) == [1, 2, 3]


def test_genetic_route_is_valid_and_not_better_than_optimum(sea):
    s, g = _node(sea, 0.1, 0.1), _node(sea, 0.1, 0.9)
    optimum = dijkstra_path(sea.graph, s, g).cost
    result = genetic_path(sea.graph, s, g, GAConfig(population_size=30, generations=60, seed=1))
    assert result.found
    assert result.path[0] == s and result.path[-1] == g
    assert len(set(result.path)) == len(result.path)              # simple path
    for a, b in zip(result.path[:-1], result.path[1:]):
        assert sea.graph.has_edge(a, b)                           # feasible route
    assert result.cost == pytest.approx(path_cost(sea.graph, result.path))
    assert result.cost >= optimum - 1e-9
    assert result.cost <= 1.10 * optimum                          # close to the optimum
    best = result.best_history
    assert all(b2 <= b1 + 1e-9 for b1, b2 in zip(best[:-1], best[1:]))   # elitism


def test_genetic_is_reproducible(sea):
    s, g = _node(sea, 0.2, 0.2), _node(sea, 0.3, 0.8)
    cfg = GAConfig(population_size=20, generations=20, seed=7)
    assert genetic_path(sea.graph, s, g, cfg).path == genetic_path(sea.graph, s, g, cfg).path


def test_route_breakdown_adds_up(sea):
    w = CostWeights()
    s, g = _node(sea, 0.1, 0.1), _node(sea, 0.1, 0.9)
    path = dijkstra_path(sea.graph, s, g).path
    b = route_breakdown(sea.graph, path, w)
    assert b["cost"] == pytest.approx(b["length_km"] + w.coastal_penalty * b["coastal_km"]
                                      + w.danger_penalty * b["danger_km"])
    assert b["cost"] == pytest.approx(path_cost(sea.graph, path))


def test_load_points_cleans_conflicts(tmp_path):
    features = []
    rows = [(0.0, 0.0, "OPEN_SEA", -100.0), (0.1, 0.1, "COASTAL_SEA", 12.0),   # conflict
            (0.2, 0.2, "NEAR_COAST", 3.0), (0.3, 0.3, "COASTLINE", -40.0),   # conflict
            (0.4, 0.4, "UNKNOWN", 0.0)]
    for lat, lon, cls, depth in rows:
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                         "properties": {"class_code": cls, "noaa_depth": depth}})
    path = tmp_path / "points.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    points, summary = load_points(path)
    assert summary.n_read == 5
    assert summary.n_unknown_class == 1
    assert summary.n_conflicts == 2
    assert len(points) == 2
    assert list(points.cls) == [0, 2]


def test_session_and_export(points, tmp_path):
    from maritime_route.pointgraph.export import export_session

    session = CourseSession()
    session.points = points
    session.set_endpoints((0.1, 0.1), (0.1, 0.9))
    session.build_graph(GraphConfig(k_neighbours=8, max_edge_km=12), area=BBOX)
    for name in ("dijkstra", "astar", "genetic"):
        session.run(name, GAConfig(population_size=20, generations=30))
    rows = {r["algorithm"]: r for r in session.comparison_rows()}
    assert rows["Dijkstra"]["gap_pct"] == pytest.approx(0.0)
    assert rows["A*"]["cost"] == pytest.approx(rows["Dijkstra"]["cost"])
    assert rows["Genetic algorithm"]["gap_pct"] >= 0.0
    files = export_session(session, tmp_path, prefix="t")
    names = {f.name for f in files}
    for expected in ("t_map.png", "t_convergence.png", "t_routes.geojson", "t_routes.csv",
                     "t_comparison.csv", "t_log.json", "t_log.txt"):
        assert expected in names
    log = json.loads((tmp_path / "t_log.json").read_text())
    assert log["session"]["ga_config"]["population_size"] == 20


def test_route_area_and_presets():
    assert route_area((10, 20), (12, 25), 2.0) == (8, 14, 18, 27)
    assert len(VOYAGES) >= 5
    for voyage in VOYAGES:
        assert -90 <= voyage.start[0] <= 90 and -180 <= voyage.start[1] <= 180


def test_main_window_starts_offscreen(monkeypatch):
    pytest.importorskip("PyQt5")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    import matplotlib
    matplotlib.use("Qt5Agg", force=True)
    from PyQt5.QtWidgets import QApplication

    from maritime_route.desktop.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(dataset=None)
    if window.thread is not None:
        window.thread.wait(60000)
    assert window.population.value() == GAConfig().population_size
    assert window.ga_config().crossover_rate == pytest.approx(GAConfig().crossover_rate)
    window.close()
