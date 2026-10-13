# Sea Course GA — course project

**Development of an application for finding the optimal course of a sea vessel over
open-sea points based on a genetic algorithm**

**Русская версия — [README_ru.md](README_ru.md)** · 中文 — [README_zh.md](README_zh.md)

Course project · Li Haoran (Ли Хаожань), group ИИ-2025 · Brest State Technical
University, Department of Intelligent Information Technologies · supervisor
A.A. Kozinsky · 2026 · document code `KP.ИИ2025.250978-01 81 00`

> This repository contains the **course project** only. The diploma project of the
> same author is a separate repository:
> <https://github.com/EDXiaoM/MaritimeRouteAI>.

## Materials

| Material | File |
|---|---|
| Explanatory note (PDF) | [`docs/note/KP_explanatory_note_Li_Haoran.pdf`](docs/note/KP_explanatory_note_Li_Haoran.pdf) |
| Explanatory note (Word) | [`docs/note/KP_explanatory_note_Li_Haoran.docx`](docs/note/KP_explanatory_note_Li_Haoran.docx) |
| Graphic material, 5 sheets A4 | [`docs/note/KP_graphic_material_5_sheets.pdf`](docs/note/KP_graphic_material_5_sheets.pdf) |
| Assignment (Russian) | [`docs/note/Assignment_course_ru.pdf`](docs/note/Assignment_course_ru.pdf) |
| **User guide** (appendix A of the note) | [`docs/User_Guide_SeaCourseGA.pdf`](docs/User_Guide_SeaCourseGA.pdf) |
| Program code | [`src/`](src), [`scripts/`](scripts), [`tests/`](tests) |
| Results of the experiments, figures, screenshots | [`docs/course/`](docs/course) |
| Dataset (152 838 points, zip 7 MB) | `merged_json_v1_course.zip` in [release v1.0](https://github.com/EDXiaoM/SeaCourseGA/releases/tag/v1.0) |

## What the program does

The desktop application (PyQt5) loads the labelled dataset (WGS-84 points of four
classes), removes points whose class contradicts their depth, builds a navigation
graph on the water points, searches a ship's course with a **genetic algorithm** and
the optimal course with **Dijkstra's** and **A\*** algorithms on the same graph, shows
the three routes on a map, plots the convergence of the genetic algorithm and saves
the results (map, convergence plot, routes in GeoJSON/CSV, comparison table,
parameter log).

## Results (section 3.4 of the note)

| Result | Value |
|---|---|
| Dataset after cleaning | 147 763 of 152 838 points (5 075 class/depth conflicts removed) |
| Test voyages | 7 (Black Sea, South China Sea, South Africa, Strait of Hormuz, Caribbean Sea) |
| Dijkstra and A\* | identical optimal cost on all voyages; A\* expands on average 1.97 times fewer nodes |
| Genetic algorithm | navigable route in all 70 runs (10 per voyage); 57 runs within 1 % of the optimum; mean gap 0.90 % |

## Files of the program

| Path | Content |
|---|---|
| `src/maritime_route/pointgraph/` | loading, graph, cost model, Dijkstra/A\*, genetic algorithm, session, export |
| `src/maritime_route/desktop/` | PyQt5 main window and background threads |
| `src/maritime_route/data/`, `routing/geodesy.py`, `config.py` | data loader, cleaning rule and spherical geometry shared with the diploma project |
| `scripts/run_desktop.py` | start of the application |
| `scripts/course_experiments.py` | all experiments of section 3.4 → `docs/course/results.json`, figures |
| `scripts/course_extra_figures.py`, `course_diagrams.py` | figures of sections 2 and 3.4 |
| `scripts/course_screenshots.py` | screenshots of the application (works without a display) |
| `scripts/course_sheets.py` | five A4 sheets of graphic material → `docs/course/sheets/` |
| `tests/` | 34 automated tests |
| `requirements-course.txt` | dependencies |

## Installation and start

Python 3.10 or newer is required (Ubuntu 20.04: install `python3.10` additionally,
e.g. from the deadsnakes PPA; Fedora 38+ and Windows: the standard Python installer).

Windows:

```bat
git clone https://github.com/EDXiaoM/SeaCourseGA.git
cd SeaCourseGA
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-course.txt
python scripts/run_desktop.py
```

Linux:

```bash
git clone https://github.com/EDXiaoM/SeaCourseGA.git
cd SeaCourseGA
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-course.txt
python scripts/run_desktop.py
```

Download `merged_json_v1_course.zip` from the
[release](https://github.com/EDXiaoM/SeaCourseGA/releases/tag/v1.0) and unpack
`merged.json` into `data/raw/`; the application then opens it automatically.
Any other file can be opened with *File → Open dataset…*.

If Qt reports *Could not load the Qt platform plugin "xcb"* on Ubuntu, install
`sudo apt install libxcb-xinerama0`.

## Reproducing the numbers of the explanatory note

```bash
python -m pytest                            # 34 tests
python scripts/course_experiments.py        # about 20 minutes, writes docs/course/results.json
python scripts/course_extra_figures.py
python scripts/course_diagrams.py
python scripts/course_sheets.py
```

The genetic algorithm uses a fixed random seed, so the routes and costs are
reproduced exactly; running times depend on the computer.
