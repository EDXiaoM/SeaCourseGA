"""Graphic material of the course project: five A4 sheets with a GOST frame.

Sheets (list of graphic material of the assignment):

1. Problem statement for the creation of the application (poster, A4)
2. Architecture of the application (poster, A4)
3. Formalisation of the problem: chromosome and fitness function (poster, A4)
4. Structural diagram of the application (drawing, A4)
5. Test results of the application (drawing, A4)

Every sheet has the frame 20-5-5-5 mm and the title block of form 1
(GOST 2.104, 185 x 55 mm). Numbers on sheet 5 are read from
``docs/course/results.json``. Output: ``docs/course/sheets/sheet_<n>.pdf``
and ``.png`` plus ``graphic_material.pdf`` with all five sheets.

Usage::

    python scripts/course_sheets.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "course" / "figures"
OUT = ROOT / "docs" / "course" / "sheets"
R = json.loads((ROOT / "docs" / "course" / "results.json").read_text(encoding="utf-8"))

CODE = "KP.ИИ2025.250978-01"
TOPIC = ("Development of an application for finding the optimal\ncourse of a sea vessel over open-sea points\nbased on a genetic algorithm")
INK = "#111111"
ACCENT = "#14507f"
PANEL = "#f3f6f9"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})
MM = 1 / 25.4


def new_sheet():
    fig = plt.figure(figsize=(210 * MM, 297 * MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 210)
    ax.set_ylim(0, 297)
    ax.set_axis_off()
    ax.add_patch(Rectangle((20, 5), 185, 287, fill=False, lw=1.6, ec=INK))
    return fig, ax


def stamp(ax, number, title, kind):
    x0, y0 = 20, 5
    lw_t, lw_n = 1.4, 0.5
    ax.add_patch(Rectangle((x0, y0), 185, 55, fill=False, lw=lw_t, ec=INK))
    cols = [7, 10, 23, 15, 10]
    xs = [x0]
    for c in cols:
        xs.append(xs[-1] + c)
    # left part: 11 rows of 5 mm
    for i in range(1, 11):
        y = y0 + 5 * i
        lw = lw_t if i in (5, 6) else lw_n
        ax.plot([x0, x0 + 65], [y, y], color=INK, lw=lw)
    for x in xs[1:]:
        ax.plot([x, x], [y0, y0 + 55], color=INK, lw=lw_t)
    labels = ["Rev.", "Sheet", "Doc. No.", "Sign.", "Date"]
    for i, lab in enumerate(labels):
        ax.text((xs[i] + xs[i + 1]) / 2, y0 + 27.5, lab, ha="center", va="center", fontsize=5.5)
    roles = [("Developed", "Li H."), ("Checked", "Kozinsky A.A."), ("T. contr.", ""),
             ("N. contr.", ""), ("Approved", "Golovko V.A.")]
    for i, (role, name) in enumerate(roles):
        y = y0 + 22.5 - 5 * i
        ax.text(x0 + 0.8, y, role, ha="left", va="center", fontsize=5.5, zorder=4)
        ax.text(xs[2] + 0.8, y, name, ha="left", va="center", fontsize=5.5)
    # the role names span the first two columns: hide the line between them
    ax.add_patch(Rectangle((xs[1] - 0.4, y0 + 0.3), 0.8, 24.4, fc="white", ec="none", zorder=3))
    # right part
    xr = x0 + 65
    ax.plot([xr, x0 + 185], [y0 + 40, y0 + 40], color=INK, lw=lw_t)
    ax.text(xr + 60, y0 + 47.5, CODE, ha="center", va="center", fontsize=13)
    ax.plot([xr + 70, xr + 70], [y0, y0 + 40], color=INK, lw=lw_t)
    ax.text(xr + 35, y0 + 25, title, ha="center", va="center", fontsize=6.5, wrap=True, linespacing=1.3)
    ax.text(xr + 35, y0 + 8, kind, ha="center", va="center", fontsize=7, weight="bold")
    xb = xr + 70     # 50 mm block: Lit. 15 | Mass 17 | Scale 18
    for y, lw in ((y0 + 35, lw_t), (y0 + 20, lw_t), (y0 + 15, lw_t)):
        ax.plot([xb, x0 + 185], [y, y], color=INK, lw=lw)
    for x in (xb + 15, xb + 32):
        ax.plot([x, x], [y0 + 20, y0 + 40], color=INK, lw=lw_t)
    for x in (xb + 5, xb + 10):
        ax.plot([x, x], [y0 + 20, y0 + 35], color=INK, lw=lw_n)
    ax.text(xb + 7.5, y0 + 37.5, "Lit.", ha="center", va="center", fontsize=5.5)
    ax.text(xb + 23.5, y0 + 37.5, "Mass", ha="center", va="center", fontsize=5.5)
    ax.text(xb + 41, y0 + 37.5, "Scale", ha="center", va="center", fontsize=5.5)
    ax.text(xb + 41, y0 + 27.5, "–", ha="center", va="center", fontsize=8)
    ax.text(xb + 23.5, y0 + 27.5, "–", ha="center", va="center", fontsize=8)
    ax.plot([xb + 25, xb + 25], [y0 + 15, y0 + 20], color=INK, lw=lw_n)
    ax.text(xb + 12.5, y0 + 17.5, f"Sheet {number}", ha="center", va="center", fontsize=5.5)
    ax.text(xb + 37.5, y0 + 17.5, "Sheets 5", ha="center", va="center", fontsize=5.5)
    ax.text(xb + 25, y0 + 7.5, "BrSTU, Dept. of IIT\ngroup ИИ-2025", ha="center", va="center", fontsize=7)


def heading(ax, text, y=285):
    ax.text(112.5, y, text, ha="center", va="top", fontsize=12, weight="bold", color=ACCENT)


def panel(ax, x, y, w, h, title=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=2", fc=PANEL,
                                ec="#b9c4ce", lw=0.6))
    if title:
        ax.text(x + 3, y + h - 3, title, ha="left", va="top", fontsize=8.5, weight="bold", color=INK)


def text_block(ax, x, y, lines, size=7.2, step=4.2):
    for i, line in enumerate(lines):
        ax.text(x, y - i * step, line, ha="left", va="top", fontsize=size, color=INK)


def image(ax, path, x, y, w, h):
    img = mpimg.imread(str(path))
    ih, iw = img.shape[0], img.shape[1]
    ratio = ih / iw
    if w * ratio > h:
        w2, h2 = h / ratio, h
    else:
        w2, h2 = w, w * ratio
    cx, cy = x + (w - w2) / 2, y + (h - h2) / 2
    ax.imshow(img, extent=(cx, cx + w2, cy, cy + h2), zorder=2)


def table(ax, x, y, col_w, rows, row_h=5.0, size=6.5):
    for r, row in enumerate(rows):
        cx = x
        for c, (cell, w) in enumerate(zip(row, col_w)):
            ax.add_patch(Rectangle((cx, y - (r + 1) * row_h), w, row_h, fill=(r == 0), fc="#dfe8f0",
                                   ec=INK, lw=0.4))
            ax.text(cx + w / 2, y - (r + 0.5) * row_h, cell, ha="center", va="center", fontsize=size,
                    weight="bold" if r == 0 else "normal")
            cx += w


# --------------------------------------------------------------------------- sheets
def sheet1():
    fig, ax = new_sheet()
    heading(ax, "Statement of the problem of creating an application\nfor finding a sea vessel's course")
    panel(ax, 25, 222, 175, 47, "Aim")
    text_block(ax, 28, 260, [
        "Develop a cross-platform desktop application that searches for the optimal course of a sea",
        "vessel over open-sea points with a genetic algorithm and compares it with Dijkstra and A*.",
        "",
        "Input: labelled dataset (WGS-84 points, 4 classes), departure and destination, parameters",
        "of the graph, penalties for dangerous zones and parameters of the genetic algorithm.",
        "Output: route of the GA, optimal routes of Dijkstra and A*, convergence plot, comparison",
        "table, files (PNG, GeoJSON, CSV, parameter log).",
    ])
    panel(ax, 25, 160, 175, 58, "Dataset of the student (after cleaning)")
    cc = R["dataset"]["class_counts"]
    rows = [["Class", "Meaning", "Points", "Role"],
            ["OPEN_SEA", "open sea", f"{cc['OPEN_SEA']:,}".replace(",", " "), "node"],
            ["COASTAL_SEA", "coastal (shallow) sea", f"{cc['COASTAL_SEA']:,}".replace(",", " "), "node, penalised"],
            ["NEAR_COAST", "land within 5 km of shore", f"{cc['NEAR_COAST']:,}".replace(",", " "), "obstacle"],
            ["COASTLINE", "inland", f"{cc['COASTLINE']:,}".replace(",", " "), "obstacle"]]
    table(ax, 28, 208, [22, 36, 16, 22], rows, row_h=5.2)
    image(ax, FIG / "fig_dataset_map.png", 128, 163, 70, 46)
    text_block(ax, 28, 179, [f"{R['dataset']['n_read']:,} points read, {R['dataset']['n_conflicts']:,} removed".replace(",", " "),
                             "(class contradicts the measured depth, tolerance 5 m)"], size=6.5)
    panel(ax, 25, 64, 175, 92, "Requirements of the assignment")
    text_block(ax, 28, 146, [
        "– Windows 10/11 and Linux (Ubuntu 20.04+, Fedora 38+); graphical user interface;",
        "– loading of the dataset from a file (WGS-84, 4 classes of points);",
        "– graph over the points: by distance or by visibility;",
        "– genetic algorithm for the ship's course; avoidance of dangerous zones,",
        "   minimisation of the path length;",
        "– settings: population size, generations, crossover and mutation probabilities,",
        "   penalties for dangerous zones;",
        "– Dijkstra and A* for comparison on the same graph;",
        "– map with the points and the three routes, convergence plot of the GA;",
        "– export: map image, routes, convergence plot, parameter log.",
        "",
        "Criterion: route cost  F(P) = L(P) + α·Lc(P) + β·Ld(P)  →  min",
        "L – length, Lc – length in coastal water, Ld – danger-weighted length near land",
    ], size=7.2, step=5.2)
    stamp(ax, 1, TOPIC, "Problem statement (poster)")
    return fig


def sheet2():
    fig, ax = new_sheet()
    heading(ax, "Architecture of the application\nfor finding a sea vessel's course")
    image(ax, FIG / "fig_architecture.png", 25, 150, 175, 125)
    rows = [["Module", "File", "Responsibility"],
            ["Loading", "dataset.py", "reading, validation, cleaning"],
            ["Graph", "graph.py", "k-NN edges, visibility test"],
            ["Cost model", "cost.py", "edge cost, fitness F(P)"],
            ["Exact search", "search.py", "Dijkstra, A*"],
            ["Genetic algorithm", "genetic.py", "encoding, operators, elitism"],
            ["Session", "session.py", "state, presets, comparison"],
            ["Visualisation", "export.py", "map, convergence, export"],
            ["GUI", "desktop/*.py", "PyQt5 window, background threads"]]
    table(ax, 32, 143, [42, 34, 85], rows, row_h=6.5, size=7)
    text_block(ax, 32, 78, ["Tools: Python 3.10+, NumPy, SciPy (k-d tree), NetworkX, Matplotlib, PyQt5, folium (optional)"],
               size=7)
    stamp(ax, 2, TOPIC, "Architecture (poster)")
    return fig


def sheet3():
    fig, ax = new_sheet()
    heading(ax, "Formalisation of the problem:\nchromosome and fitness function")
    panel(ax, 25, 200, 175, 72, "Navigation graph and fitness function")
    text_block(ax, 28, 263, [
        "G = (V, E):  V – water points (OPEN_SEA, COASTAL_SEA) of the area;",
        "E – k nearest neighbours closer than l_max, segments that cross land are removed (visibility test).",
        "",
        "Edge cost:     c(e) = l(e) · (1 + α·s(e) + β·φ(e)),     φ(e) = max(0, 1 − d_land(e) / r)",
        "Fitness:        F(P) = Σ c(e) = L(P) + α·Lc(P) + β·Ld(P)  →  min",
        "Quality:        δ = (F_GA − F*) / F* · 100 %,   F* – optimum of Dijkstra / A*",
        "",
        "l(e) – great-circle length (haversine), s(e) – share in coastal water, d_land(e) – distance to land,",
        "α, β – penalties, r – radius of the danger zone. c(e) ≥ l(e), so h = d_gc is admissible for A*.",
    ], size=7, step=5.0)
    image(ax, FIG / "fig_chromosome.png", 25, 92, 175, 105)
    panel(ax, 25, 64, 175, 26, None)
    text_block(ax, 28, 87, [
        "Initial population: random walks s → t, p(v|u) ~ exp(κ·γ), κ ∈ [1; 15], 50 % through an intermediate node",
        "Selection: tournament (k = 3);  crossover: one point at a common node, p_c = 0.8",
        "Mutation (p_m = 0.3): re-routing (60 %) or shortcut (40 %);  elitism: e = 2",
        "Stop: G_max = 300 generations, 80 generations without improvement or user request",
    ], size=7, step=5.0)
    stamp(ax, 3, TOPIC, "Formalisation (poster)")
    return fig


def sheet4():
    fig, ax = new_sheet()
    heading(ax, "Structural diagram of the application")
    image(ax, FIG / "fig_structure.png", 25, 66, 175, 205)
    stamp(ax, 4, TOPIC, "Structural diagram (drawing)")
    return fig


def sheet5():
    fig, ax = new_sheet()
    heading(ax, "Test results of the application")
    image(ax, FIG / "fig_route_CapeTown_Gqeberha.png", 25, 205, 175, 72)
    ax.text(112.5, 205, "Routes of the voyage Cape Town – Gqeberha (seed 0)", ha="center", fontsize=7)
    image(ax, FIG / "fig_convergence_pair.png", 25, 152, 175, 52)
    ax.text(112.5, 151, "Convergence of the GA: Odesa – Batumi, Cape Town – Gqeberha", ha="center", fontsize=7)
    rows = [["Voyage", "F*", "Exp. Dijkstra / A*", "Time D / A*, ms", "GA mean gap, %", "GA ≤ 1 %", "GA time, s"]]
    for v in R["voyages"]:
        d, a, g = v["dijkstra"], v["astar"], v["genetic"]
        rows.append([v["name"].split(" (")[0].replace(" - ", " – "), f"{d['cost']:.1f}",
                     f"{d['expanded']} / {a['expanded']}",
                     f"{1000 * d['runtime_median_s']:.0f} / {1000 * a['runtime_median_s']:.0f}",
                     f"{g['gap_mean']:.2f}", f"{g['within_1pct']} of {g['n']}", f"{g['time_mean']:.1f}"])
    table(ax, 26, 145, [36, 18, 30, 26, 24, 18, 21], rows, row_h=5.6, size=6.4)
    voy = R["voyages"]
    ratio = sum(v["dijkstra"]["expanded"] / v["astar"]["expanded"] for v in voy) / len(voy)
    all_in = sum(v["genetic"]["within_1pct"] == v["genetic"]["n"] for v in voy)
    runs = sum(v["genetic"]["n"] for v in voy)
    crossing = sum(v["distance_route"]["edges_crossing_land"] > 0 for v in voy)
    ops = {r["variant"]: r["gap_mean"] for r in
           R["sensitivity"]["blocks"]["Cape Town - Gqeberha (South Africa)"]["operators"]}
    text_block(ax, 28, 97, [
        f"– Dijkstra and A* give the same optimum; A* expands on average {ratio:.2f} times fewer nodes;",
        f"– the GA found valid routes in all {runs} runs; on {all_in} of {len(voy)} voyages every run was "
        f"within 1 % of the optimum;",
        f"– on the graph built by distance the optimal route crossed land on {crossing} of {len(voy)} voyages;",
        "– without intermediate nodes in the random walks the mean gap on Cape Town – Gqeberha",
        f"   grows from {ops['full operator set']:.2f} % to {ops['without intermediate nodes']:.2f} %.",
    ], size=7, step=5.2)
    stamp(ax, 5, TOPIC, "Test results (drawing)")
    return fig


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with PdfPages(OUT / "graphic_material.pdf") as pdf:
        for i, make in enumerate((sheet1, sheet2, sheet3, sheet4, sheet5), 1):
            fig = make()
            fig.savefig(OUT / f"sheet_{i}.pdf")
            fig.savefig(OUT / f"sheet_{i}.png", dpi=200)
            pdf.savefig(fig)
            plt.close(fig)
            print("written", OUT / f"sheet_{i}.pdf")


if __name__ == "__main__":
    main()
