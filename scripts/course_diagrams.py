"""Schematic figures of the course project explanatory note.

Writes to ``docs/course/figures``:

* ``fig_architecture.png``  - modules of the application and the data flow;
* ``fig_structure.png``     - main classes and their relations;
* ``fig_ui_layout.png``     - layout of the main window;
* ``fig_chromosome.png``    - route encoding, crossover and the two mutations;
* ``fig_ga_flowchart.png``  - flowchart of the genetic algorithm.

All drawings are made with Matplotlib in millimetre coordinates so that the
printed size is known (figures are inserted 160-165 mm wide).

Usage::

    python scripts/course_diagrams.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "course" / "figures"
MM = 1 / 25.4
INK = "#1f1f1d"
GREY = "#6b6b66"
FILL = "#eef3f7"
FILL2 = "#fbf3e3"
ACCENT = "#14507f"
ORANGE = "#d1561f"
GREEN = "#1a8f6a"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})


def canvas(w_mm: float, h_mm: float):
    fig = plt.figure(figsize=(w_mm * MM, h_mm * MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w_mm)
    ax.set_ylim(0, h_mm)
    ax.set_axis_off()
    return fig, ax


def box(ax, x, y, w, h, text, fill="white", edge=INK, size=8, weight="normal", lw=0.9,
        rounded=True, align="center", va="center", family=None):
    style = "round,pad=0,rounding_size=1.6" if rounded else "square,pad=0"
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style, fc=fill, ec=edge, lw=lw))
    if align == "center":
        ax.text(x + w / 2, y + h / 2, text, ha="center", va=va, fontsize=size, weight=weight,
                color=INK, family=family, linespacing=1.25)
    else:
        ax.text(x + 2, y + h - 2, text, ha="left", va="top", fontsize=size, weight=weight,
                color=INK, family=family, linespacing=1.3)


def arrow(ax, p, q, color=INK, lw=0.9, style="-|>", ls="-", rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=8, color=color, lw=lw,
                                 linestyle=ls, shrinkA=0, shrinkB=0,
                                 connectionstyle=f"arc3,rad={rad}"))


def save(fig, name):
    fig.savefig(FIG / name, dpi=300)
    plt.close(fig)
    print("written", FIG / name)


# --------------------------------------------------------------------------
def architecture():
    fig, ax = canvas(165, 122)
    bands = [(100, 20, "Presentation layer (PyQt5)"), (66, 30, "Application layer"),
             (1, 61, "Domain layer: package maritime_route.pointgraph")]
    for y, h, label in bands:
        ax.add_patch(Rectangle((2, y), 128, h, fc="#f7f7f5", ec="#c9c9c4", lw=0.7))
        ax.text(4, y + h - 1.5, label, ha="left", va="top", fontsize=7.5, color=GREY, style="italic")
    box(ax, 6, 102, 62, 12, "MainWindow\ncontrol panel; tabs Map, Convergence,\nComparison, Log", FILL)
    box(ax, 80, 102, 46, 12, "TaskThread (QThread)\nlong operations in\nthe background", FILL)
    arrow(ax, (68, 108), (80, 108))
    ax.text(74, 109.5, "starts", ha="center", fontsize=6.5, color=GREY)
    box(ax, 22, 69, 88, 20,
        "CourseSession - state of one working session\n\nload()   set_endpoints()   build_graph()\nset_weights()   run()   comparison_rows()",
        FILL2)
    arrow(ax, (37, 102), (45, 89))
    ax.text(30, 95, "parameters,\nend points", fontsize=6.5, color=GREY, ha="center")
    arrow(ax, (103, 102), (95, 89))
    ax.text(112, 95, "progress,\nresults", fontsize=6.5, color=GREY, ha="center")
    arrow(ax, (66, 69), (66, 60.5), lw=1.4)
    ax.text(68, 63.5, "calls the module functions", fontsize=6.5, color=GREY)
    cols = (6, 48, 90)
    w, h = 36, 19
    row1, row2 = 38, 13
    box(ax, cols[0], row1, w, h, "3. Cost model\ncost.py\n\nedge cost c(e),\nfitness F(P)", "white", size=7)
    box(ax, cols[1], row1, w, h, "2. Graph module\ngraph.py\n\nbuild_graph(), SeaGraph,\nk-NN edges, visibility", "white", size=7)
    box(ax, cols[2], row1, w, h, "1. Loading module\ndataset.py\n\nload_points(), PointSet,\nvalidation, cleaning", "white", size=7)
    box(ax, cols[0], row2, w, h, "4. Exact search\nsearch.py\n\ndijkstra_path(),\nastar_path()", "white", size=7)
    box(ax, cols[1], row2, w, h, "5. Genetic algorithm\ngenetic.py\n\nGAConfig, genetic_path()", "white", size=7)
    box(ax, cols[2], row2, w, h, "6. Visualisation, export\nexport.py\n\ndraw_map(),\ndraw_convergence(),\nexport_session()", "white", size=6.8)
    C = ACCENT
    arrow(ax, (cols[2], row1 + h / 2), (cols[1] + w, row1 + h / 2), color=C, lw=1.2)
    arrow(ax, (cols[1], row1 + h / 2), (cols[0] + w, row1 + h / 2), color=C, lw=1.2)
    arrow(ax, (cols[0] + w / 2, row1), (cols[0] + w / 2, row2 + h), color=C, lw=1.2)
    arrow(ax, (cols[0] + w - 4, row1), (cols[1] + 6, row2 + h), color=C, lw=1.2)
    arrow(ax, (cols[1] + w, row2 + h / 2), (cols[2], row2 + h / 2), color=C, lw=1.2)
    arrow(ax, (cols[0] + w / 2, row2), (cols[2] + w / 2, row2), color=C, lw=1.2, rad=0.15)
    # external files
    box(ax, 134, 40, 29, 15, "dataset file\nGeoJSON / CSV /\nJSON, WGS-84", "white", size=6.5, rounded=False)
    box(ax, 134, 15, 29, 15, "export folder\nPNG, GeoJSON,\nCSV, JSON / TXT log", "white", size=6.5, rounded=False)
    arrow(ax, (134, 47.5), (cols[2] + w, 47.5), color=C, lw=1.2)
    arrow(ax, (cols[2] + w, 22.5), (134, 22.5), color=C, lw=1.2)
    ax.plot([134, 141], [116, 116], color=C, lw=1.2)
    ax.text(143, 116, "data flow", va="center", fontsize=6.5)
    ax.plot([134, 141], [111, 111], color=INK, lw=0.9)
    ax.text(143, 111, "control", va="center", fontsize=6.5)
    save(fig, "fig_architecture.png")


# --------------------------------------------------------------------------
def structure():
    fig, ax = canvas(165, 138)
    LH = 3.4

    def cls(x, top, w, name, attrs, methods, fill=FILL, ht=6):
        ha = LH * len(attrs) + 2
        hm = LH * len(methods) + 2 if methods else 0
        h = ht + ha + hm
        y = top - h
        ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=INK, lw=0.8))
        ax.add_patch(Rectangle((x, top - ht), w, ht, fc=fill, ec=INK, lw=0.8))
        ax.text(x + w / 2, top - ht / 2, name, ha="center", va="center", fontsize=7.5, weight="bold")
        for i, a in enumerate(attrs):
            ax.text(x + 1.5, top - ht - 2.6 - LH * i, a, fontsize=6.3, family="DejaVu Sans Mono")
        if methods:
            yl = top - ht - ha
            ax.plot([x, x + w], [yl, yl], color=INK, lw=0.6)
            for i, m in enumerate(methods):
                ax.text(x + 1.5, yl - 2.6 - LH * i, m, fontsize=6.3, family="DejaVu Sans Mono")
        return x, y, w, h

    def diamond(px, py, horizontal=False):
        if horizontal:
            pts = [(px, py), (px + 1.8, py + 1.1), (px + 3.6, py), (px + 1.8, py - 1.1)]
        else:
            pts = [(px, py), (px + 1.1, py - 1.8), (px, py - 3.6), (px - 1.1, py - 1.8)]
        ax.add_patch(Polygon(pts, closed=True, fc=INK, ec=INK, lw=0.6))

    def poly(pts, ls="-"):
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=INK, lw=0.7, ls=ls)

    def mult(x, y, t):
        ax.text(x, y, t, fontsize=6.3, color=GREY)

    mw = cls(4, 134, 54, "MainWindow", ["session: CourseSession", "thread: TaskThread"],
             ["start_build()", "start_runs(algorithms)", "export_results()"])
    tt = cls(108, 134, 54, "TaskThread (QThread)", ["signals: progress, generation,", "succeeded, failed"],
             ["run()", "request_stop()"])
    cs = cls(50, 98, 64, "CourseSession",
             ["points: PointSet", "sea: SeaGraph", "weights: CostWeights", "ga_config: GAConfig",
              "runs: dict[str, RouteRun]"],
             ["load(path)", "build_graph(config, area)", "set_weights(weights)", "run(algorithm)",
              "comparison_rows()"], FILL2)
    ps = cls(2, 92, 42, "PointSet", ["lat, lon: float64[n]", "cls: int8[n]", "region: str[n]"],
             ["in_bbox(bbox)", "select(mask)"])
    rr = cls(120, 98, 42, "RouteRun", ["result: PathResult", "breakdown: dict", "coords: list"], [])
    pr = cls(120, 74, 42, "PathResult", ["algorithm, found", "path, cost", "expanded, runtime_s",
                                         "best_history"], [])
    sg = cls(2, 40, 50, "SeaGraph", ["graph: networkx.Graph", "lat, lon, cls: arrays",
                                      "config: GraphConfig", "stats: GraphStats", "component: int[n]"],
             ["nearest_node(lat, lon)"])
    gc = cls(58, 30, 34, "GraphConfig", ["mode", "k_neighbours", "max_edge_km", "sample_step_km"], [])
    cw = cls(96, 40, 30, "CostWeights", ["coastal_penalty", "danger_penalty", "danger_radius_km"], [])
    ga = cls(130, 40, 33, "GAConfig", ["population_size", "generations", "crossover_rate",
                                        "mutation_rate", "tournament_size", "elite, seed"], [])
    # MainWindow -> CourseSession (composition)
    x0 = 40
    diamond(x0, mw[1])
    poly([(x0, mw[1] - 3.6), (x0, 103), (60, 103), (60, 98)])
    mult(61, 99.5, "1")
    # MainWindow - - -> TaskThread
    poly([(mw[0] + mw[2], 118), (tt[0], 118)], ls="--")
    ax.add_patch(FancyArrowPatch((tt[0] - 4, 118), (tt[0], 118), arrowstyle="-|>", mutation_scale=7, color=INK, lw=0.7))
    ax.text((mw[0] + mw[2] + tt[0]) / 2, 119.3, "creates", ha="center", fontsize=6.3, color=GREY)
    # CourseSession -> PointSet
    yps = 80
    diamond(cs[0] - 3.6, yps, horizontal=True)
    poly([(ps[0] + ps[2], yps), (cs[0] - 3.6, yps)])
    mult(ps[0] + ps[2] + 1, yps + 1, "1")
    # CourseSession -> RouteRun
    yrr = 90
    diamond(cs[0] + cs[2], yrr, horizontal=True)
    poly([(cs[0] + cs[2] + 3.6, yrr), (rr[0], yrr)])
    mult(rr[0] - 3, yrr + 1, "*")
    # RouteRun -> PathResult
    diamond(141, rr[1])
    poly([(141, rr[1] - 3.6), (141, 74)])
    mult(142.5, 75.5, "1")
    # CourseSession -> SeaGraph, CostWeights, GAConfig
    yb = cs[1]
    for xs, xt, top, mid in ((58, 27, 40, 45), (96, 111, 40, 46.5), (108, 146, 40, 43.5)):
        diamond(xs, yb)
        poly([(xs, yb - 3.6), (xs, mid), (xt, mid), (xt, top)])
        mult(xt + 1, top + 1, "0..1" if xt == 27 else "1")
    # SeaGraph -> GraphConfig
    diamond(sg[0] + sg[2], 26, horizontal=True)
    poly([(sg[0] + sg[2] + 3.6, 26), (gc[0], 26)])
    mult(gc[0] - 3, 27, "1")
    ax.text(2, 2.5, "Filled diamond - composition (the owner keeps the object); dashed arrow - creation.",
            fontsize=6.5, color=GREY)
    save(fig, "fig_structure.png")


# --------------------------------------------------------------------------
def ui_layout():
    fig, ax = canvas(165, 104)
    ax.add_patch(Rectangle((1, 1), 163, 102, fc="white", ec=INK, lw=1.0))
    ax.add_patch(Rectangle((1, 97), 163, 6, fc="#e6e6e3", ec=INK, lw=0.8))
    ax.text(3, 100, "Menu: File (Open dataset, Export results, Exit), Help (About)", va="center", fontsize=7)
    ax.add_patch(Rectangle((1, 1), 163, 5, fc="#e6e6e3", ec=INK, lw=0.8))
    ax.text(3, 3.5, "Status bar: current operation, GA generation, best cost", va="center", fontsize=7)
    ax.add_patch(Rectangle((140, 2), 22, 3, fc="white", ec=GREY, lw=0.6))
    ax.text(151, 3.5, "progress bar", ha="center", va="center", fontsize=6, color=GREY)
    groups = [("1. Dataset", "file name, Open..., cleaning\ncheck box, class counts", 12),
              ("2. Route", "preset, departure and destination\nlatitude/longitude, pick on map", 14),
              ("3. Graph", "area, margin, edge mode, k,\nmax edge length, visibility step", 14),
              ("4. Penalties", "alpha, beta, danger radius r", 9),
              ("5. Genetic algorithm", "population, generations, crossover,\nmutation, tournament, elite, seed", 14),
              ("6. Run", "GA | Dijkstra | A* | Run all | Stop\nExport results...", 12)]
    y = 95
    for title, text, h in groups:
        y -= h + 1.6
        ax.add_patch(Rectangle((3, y), 50, h, fc=FILL, ec=ACCENT, lw=0.7))
        ax.text(5, y + h - 2.2, title, fontsize=7, weight="bold", va="center")
        ax.text(5, y + h - 4.8, text, fontsize=6.2, va="top", color=INK, linespacing=1.25)
    ax.text(28, 8.2, "scrollable control panel", ha="center", fontsize=6.5, color=GREY, style="italic")
    # right area
    tabs = ["Map", "Convergence", "Comparison", "Log"]
    x = 58
    for i, t in enumerate(tabs):
        w = 9 + 1.6 * len(t)
        ax.add_patch(Rectangle((x, 89), w, 6, fc="white" if i == 0 else "#e6e6e3", ec=INK, lw=0.7))
        ax.text(x + w / 2, 92, t, ha="center", va="center", fontsize=7)
        x += w
    ax.add_patch(Rectangle((58, 8), 104, 81, fc="white", ec=INK, lw=0.8))
    ax.add_patch(Rectangle((60, 82), 60, 5, fc="#f3f3f1", ec=GREY, lw=0.5))
    ax.text(90, 84.5, "Matplotlib toolbar: home, pan, zoom, save", ha="center", va="center", fontsize=6.2)
    ax.add_patch(Rectangle((60, 10), 100, 70, fc="#f2f6fa", ec=GREY, lw=0.5))
    ax.text(110, 52, "Map: points of the four classes (WGS-84),\ngraph edges (optional), departure and destination,\n"
            "routes of the GA, Dijkstra and A*\n\nclick = place departure / destination",
            ha="center", va="center", fontsize=7, linespacing=1.4)
    ax.text(110, 20, "Convergence tab: best and median cost per generation\n"
            "Comparison tab: table of the three algorithms\nLog tab: messages and parameters",
            ha="center", va="center", fontsize=6.3, color=GREY, linespacing=1.4)
    save(fig, "fig_ui_layout.png")


# --------------------------------------------------------------------------
def chromosome():
    fig, ax = canvas(165, 112)
    # a) encoding
    ax.text(2, 109, "a) chromosome = route of variable length", fontsize=8, weight="bold", va="top")
    genes = ["s", "v12", "v40", "v41", "v77", "v80", "v95", "t"]
    for i, g in enumerate(genes):
        fill = "#d9e7f2" if g in ("s", "t") else "white"
        box(ax, 6 + i * 13, 92, 11.5, 8, g, fill, rounded=False, size=8)
    ax.text(6 + 8 * 13 + 2, 96, "neighbouring genes are joined\nby an edge of the graph G;\nno node is repeated", fontsize=7,
            va="center", color=GREY)
    # b) crossover
    ax.text(2, 86, "b) one-point crossover at a common node c", fontsize=8, weight="bold", va="top")
    pa = ["s", "a1", "a2", "c", "a4", "a5", "t"]
    pb = ["s", "b1", "c", "b3", "b4", "b5", "b6", "t"]

    def row(y, genes, label, colours):
        ax.text(4, y + 4, label, fontsize=7.5, va="center")
        for i, (g, col) in enumerate(zip(genes, colours)):
            fill = "#ffd8c2" if g == "c" else col
            box(ax, 26 + i * 13, y, 11.5, 8, g, fill, rounded=False, size=7.5)

    A, B = "#e7f0f8", "#eaf5ec"
    row(70, pa, "parent 1", [A] * len(pa))
    row(60, pb, "parent 2", [B] * len(pb))
    row(46, ["s", "a1", "a2", "c", "b3", "b4", "b5", "b6", "t"], "child 1", [A, A, A, A, B, B, B, B, B])
    row(36, ["s", "b1", "c", "a4", "a5", "t"], "child 2", [B, B, B, A, A, A])
    ax.text(110, 40, "head of one parent up to c +\ntail of the other parent after c;\nloops are cut out", fontsize=7,
            color=GREY, va="center")
    # c) mutations
    ax.text(2, 29, "c) mutations", fontsize=8, weight="bold", va="top")
    # re-routing sketch
    xs = [6, 18, 30, 42, 54, 66]
    ys = [10, 14, 12, 16, 12, 10]
    ax.plot(xs, ys, "-o", color=ACCENT, ms=3, lw=1.2)
    ax.plot([18, 26, 36, 46, 54], [14, 22, 24, 21, 12], "--o", color=ORANGE, ms=3, lw=1.2)
    ax.text(36, 3, "re-routing: the part $v_i \\ldots v_j$ is replaced\nby a new random walk", ha="center", fontsize=6.8)
    xs2 = [95, 105, 112, 120, 130, 142, 152]
    ys2 = [10, 18, 9, 19, 11, 17, 10]
    ax.plot(xs2, ys2, "-o", color=ACCENT, ms=3, lw=1.2)
    ax.plot([105, 142], [18, 17], "--", color=GREEN, lw=1.6)
    ax.text(124, 3, "shortcut: the sub-route $v_i \\ldots v_j$ is replaced by the\ndirect edge $(v_i, v_j)$ if it exists and is cheaper",
            ha="center", fontsize=6.8)
    save(fig, "fig_chromosome.png")


# --------------------------------------------------------------------------
def flowchart():
    fig, ax = canvas(150, 178)
    cx = 70
    w = 76

    def step(y, text, h=10, fill="white", shape="box"):
        if shape == "term":
            ax.add_patch(FancyBboxPatch((cx - 30, y), 60, h, boxstyle="round,pad=0,rounding_size=3.9",
                                        fc=FILL, ec=INK, lw=0.9))
            ax.text(cx, y + h / 2, text, ha="center", va="center", fontsize=7.5)
        else:
            box(ax, cx - w / 2, y, w, h, text, fill, rounded=False, size=7.2)

    def diamond(y, text, h=14, wd=70):
        ax.add_patch(Polygon([(cx, y + h), (cx + wd / 2, y + h / 2), (cx, y), (cx - wd / 2, y + h / 2)],
                             closed=True, fc=FILL2, ec=INK, lw=0.9))
        ax.text(cx, y + h / 2, text, ha="center", va="center", fontsize=7)

    def line(pts):
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=INK, lw=0.9)

    step(168, "Start", 8, shape="term")
    step(154, "Input: graph G with edge costs, nodes s and t,\nparameters N, $G_{max}$, $p_c$, $p_m$, k, e")
    step(140, "Initial population: N random walks s \u2192 t\n(goal attraction \u03ba, optional intermediate node)")
    step(126, "Evaluate the fitness F(P) of every route;\nremember the best route P*")
    diamond(108, "stop criterion?\n$G_{max}$ reached, stagnation\nor user request")
    step(94, "Copy e elite routes to the new population")
    step(80, "Tournament selection of two parents (size k)")
    step(66, "With probability $p_c$: crossover at a common\nnode, removal of loops")
    step(52, "With probability $p_m$: mutation of each child\n(re-routing or shortcut)")
    diamond(34, "new population\ncomplete?", 13, 56)
    step(20, "Replace the population, evaluate F,\nupdate P* and the convergence curves")
    step(4, "Output: best route P*, its cost F(P*),\nconvergence curves", 10, fill=FILL)
    for y0, y1 in ((168, 164), (154, 150), (140, 136), (126, 122), (108, 104), (94, 90), (80, 76),
                   (66, 62), (52, 47), (34, 30)):
        arrow(ax, (cx, y0), (cx, y1))
    ax.text(cx + 2, 105.5, "no", fontsize=7)
    ax.text(cx + 2, 31.5, "yes", fontsize=7)
    # "yes" of the stop test: left side down to the output
    line([(cx - 35, 115), (cx - 54, 115), (cx - 54, 9)])
    arrow(ax, (cx - 54, 9), (cx - w / 2, 9))
    ax.text(cx - 44, 116.5, "yes", fontsize=7)
    # "no" of the population test: back to the selection
    line([(cx - 28, 40.5), (cx - 46, 40.5), (cx - 46, 85)])
    arrow(ax, (cx - 46, 85), (cx - w / 2, 85))
    ax.text(cx - 38, 42, "no", fontsize=7)
    # next generation: back to the stop test
    line([(cx + w / 2, 25), (cx + 46, 25), (cx + 46, 124), (cx + 0.6, 124)])
    ax.add_patch(FancyArrowPatch((cx + 8, 124), (cx + 0.5, 124), arrowstyle="-|>", mutation_scale=8,
                                 color=INK, lw=0.9))
    ax.text(cx + 48, 75, "next generation", fontsize=7, rotation=90, va="center")
    save(fig, "fig_ga_flowchart.png")


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    architecture()
    structure()
    ui_layout()
    chromosome()
    flowchart()


if __name__ == "__main__":
    main()
