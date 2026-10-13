"""Main window of the desktop application "Sea Course GA".

Layout
------
* Left: a scrollable control panel with six groups - *Dataset*, *Route*,
  *Graph*, *Penalties*, *Genetic algorithm* and the run buttons.
* Right: four tabs - *Map* (points, graph and routes, with the Matplotlib
  navigation toolbar), *Convergence* (best and median cost per generation),
  *Comparison* (table of the three algorithms) and *Log*.
* Bottom: status bar with a progress bar.

Work flow: open the dataset -> choose a preset or set the departure and the
destination (typed or clicked on the map) -> build the graph -> run the
genetic algorithm, Dijkstra and A* (or all three) -> export the results.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, Optional

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAction, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QMainWindow, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSpinBox, QSplitter,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from ..config import APP_AUTHOR, PROJECT_ROOT, RAW_DIR
from ..pointgraph.cost import CostWeights
from ..pointgraph.dataset import region_bbox, region_names
from ..pointgraph.export import draw_convergence, draw_map, export_session
from ..pointgraph.genetic import GAConfig
from ..pointgraph.graph import GraphConfig
from ..pointgraph.session import ALGORITHM_LABEL, VOYAGES, CourseSession
from .workers import TaskThread

APP_TITLE = "Sea Course GA - ship course search on open-sea points"
AROUND_ROUTE = "Around the route"


def _spin(minimum: float, maximum: float, value: float, step: float = 1.0,
          decimals: int = 0, suffix: str = ""):
    """Integer or decimal spin box with the given range and value."""
    if decimals == 0:
        box = QSpinBox()
        box.setRange(int(minimum), int(maximum))
        box.setSingleStep(int(step))
        box.setValue(int(value))
    else:
        box = QDoubleSpinBox()
        box.setDecimals(decimals)
        box.setRange(minimum, maximum)
        box.setSingleStep(step)
        box.setValue(value)
    if suffix:
        box.setSuffix(suffix)
    box.setKeyboardTracking(False)
    return box


class PlotCanvas(FigureCanvasQTAgg):
    """Matplotlib figure embedded in a Qt widget."""

    def __init__(self, width: float = 8.0, height: float = 6.0) -> None:
        self.figure = Figure(figsize=(width, height))
        super().__init__(self.figure)


class MainWindow(QMainWindow):
    """The application window; owns one :class:`CourseSession`."""

    def __init__(self, dataset: Optional[Path] = None) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1400, 860)
        self.session = CourseSession()
        self.thread: Optional[TaskThread] = None
        self.graph_dirty = True
        self.pick_mode: Optional[str] = None       # "start", "goal" or None
        self._build_menu()
        self._build_ui()
        self._set_busy(False)
        self._apply_preset(0)
        self.redraw_map()
        self.redraw_convergence()
        default = dataset or self._default_dataset()
        if default is not None and default.exists():
            self.load_dataset(default)

    # ================================================================ layout
    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("&File")
        action = QAction("&Open dataset...", self)
        action.setShortcut("Ctrl+O")
        action.triggered.connect(self.choose_dataset)
        menu.addAction(action)
        action = QAction("&Export results...", self)
        action.setShortcut("Ctrl+E")
        action.triggered.connect(self.export_results)
        menu.addAction(action)
        menu.addSeparator()
        action = QAction("E&xit", self)
        action.triggered.connect(self.close)
        menu.addAction(action)
        help_menu = self.menuBar().addMenu("&Help")
        action = QAction("&About", self)
        action.triggered.connect(self.show_about)
        help_menu.addAction(action)

    def _build_ui(self) -> None:
        panel = QWidget()
        column = QVBoxLayout(panel)
        column.addWidget(self._dataset_group())
        column.addWidget(self._route_group())
        column.addWidget(self._graph_group())
        column.addWidget(self._penalty_group())
        column.addWidget(self._ga_group())
        column.addWidget(self._run_group())
        column.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidget(panel)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        panel.setMinimumWidth(410)
        scroll.setMinimumWidth(430)

        self.tabs = QTabWidget()
        self.map_canvas = PlotCanvas(9, 7)
        self.map_canvas.mpl_connect("button_press_event", self._on_map_click)
        map_page = QWidget()
        map_layout = QVBoxLayout(map_page)
        map_layout.addWidget(NavigationToolbar2QT(self.map_canvas, map_page))
        map_layout.addWidget(self.map_canvas)
        self.tabs.addTab(map_page, "Map")
        self.conv_canvas = PlotCanvas(9, 6)
        conv_page = QWidget()
        conv_layout = QVBoxLayout(conv_page)
        conv_layout.addWidget(NavigationToolbar2QT(self.conv_canvas, conv_page))
        conv_layout.addWidget(self.conv_canvas)
        self.tabs.addTab(conv_page, "Convergence")
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "Algorithm", "Cost F", "Length, km", "Coastal, km", "Danger, km",
            "To land, km", "Effort*", "Time, s", "Gap, %"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        table_page = QWidget()
        table_layout = QVBoxLayout(table_page)
        table_layout.addWidget(self.table)
        note = QLabel(
            "* Effort: nodes expanded (Dijkstra, A*) or fitness evaluations (genetic algorithm). "
            "To land: closest approach of the route to a land point. Gap: excess of the cost "
            "over the optimum found by Dijkstra/A*.")
        note.setWordWrap(True)
        table_layout.addWidget(note)
        self.graph_info = QLabel("")
        self.graph_info.setWordWrap(True)
        table_layout.addWidget(self.graph_info)
        self.tabs.addTab(table_page, "Comparison")
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.tabs.addTab(self.log_view, "Log")

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(scroll)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([440, 960])
        self.setCentralWidget(splitter)

        self.progress = QProgressBar()
        self.progress.setMaximumWidth(260)
        self.progress.setRange(0, 100)
        self.statusBar().addPermanentWidget(self.progress)
        self.statusBar().showMessage("Ready")

    def _dataset_group(self) -> QGroupBox:
        box = QGroupBox("1. Dataset (WGS-84, 4 classes)")
        layout = QVBoxLayout(box)
        row = QHBoxLayout()
        self.dataset_label = QLabel("No dataset loaded")
        self.dataset_label.setWordWrap(True)
        self.open_button = QPushButton("Open...")
        self.open_button.clicked.connect(self.choose_dataset)
        row.addWidget(self.dataset_label, 1)
        row.addWidget(self.open_button)
        layout.addLayout(row)
        self.clean_check = QCheckBox("Remove class/depth conflicts (5 m)")
        self.clean_check.setChecked(True)
        layout.addWidget(self.clean_check)
        self.dataset_info = QLabel("")
        self.dataset_info.setWordWrap(True)
        layout.addWidget(self.dataset_info)
        return box

    def _route_group(self) -> QGroupBox:
        box = QGroupBox("2. Route")
        form = QFormLayout(box)
        self.preset = QComboBox()
        self.preset.addItems([v.name for v in VOYAGES])
        self.preset.addItem("(custom)")
        self.preset.currentIndexChanged.connect(self._apply_preset)
        form.addRow("Preset:", self.preset)
        self.start_lat = _spin(-90, 90, 0, 0.1, 4, " deg")
        self.start_lon = _spin(-180, 180, 0, 0.1, 4, " deg")
        self.goal_lat = _spin(-90, 90, 0, 0.1, 4, " deg")
        self.goal_lon = _spin(-180, 180, 0, 0.1, 4, " deg")
        for widget in (self.start_lat, self.start_lon, self.goal_lat, self.goal_lon):
            widget.valueChanged.connect(self._endpoints_edited)
        form.addRow("Departure latitude:", self.start_lat)
        form.addRow("Departure longitude:", self.start_lon)
        form.addRow("Destination latitude:", self.goal_lat)
        form.addRow("Destination longitude:", self.goal_lon)
        row = QHBoxLayout()
        self.pick_start = QPushButton("Pick departure")
        self.pick_goal = QPushButton("Pick destination")
        for button, mode in ((self.pick_start, "start"), (self.pick_goal, "goal")):
            button.setCheckable(True)
            button.toggled.connect(lambda on, m=mode: self._set_pick_mode(m if on else None))
            row.addWidget(button)
        form.addRow(row)
        return box

    def _graph_group(self) -> QGroupBox:
        box = QGroupBox("3. Graph")
        form = QFormLayout(box)
        self.area = QComboBox()
        self.area.addItem(AROUND_ROUTE)
        self.area.addItems(region_names())
        self.area.currentIndexChanged.connect(self._graph_edited)
        form.addRow("Area:", self.area)
        self.margin = _spin(0.5, 10, 2.0, 0.5, 1, " deg")
        self.margin.valueChanged.connect(self._graph_edited)
        form.addRow("Margin around route:", self.margin)
        self.mode = QComboBox()
        self.mode.addItems(["By visibility", "By distance"])
        self.mode.currentIndexChanged.connect(self._graph_edited)
        form.addRow("Edges:", self.mode)
        self.k_neighbours = _spin(2, 30, 10)
        self.k_neighbours.valueChanged.connect(self._graph_edited)
        form.addRow("Nearest neighbours k:", self.k_neighbours)
        self.max_edge = _spin(2, 200, 40, 5, 1, " km")
        self.max_edge.valueChanged.connect(self._graph_edited)
        form.addRow("Maximal edge length:", self.max_edge)
        self.sample_step = _spin(0.2, 10, 1.0, 0.1, 1, " km")
        self.sample_step.valueChanged.connect(self._graph_edited)
        form.addRow("Visibility test step:", self.sample_step)
        self.build_button = QPushButton("Build graph")
        self.build_button.clicked.connect(lambda: self.start_build())
        self.show_edges = QCheckBox("Show edges")
        self.show_edges.toggled.connect(lambda _: self.redraw_map())
        row = QHBoxLayout()
        row.addWidget(self.build_button)
        row.addWidget(self.show_edges)
        form.addRow(row)
        return box

    def _penalty_group(self) -> QGroupBox:
        box = QGroupBox("4. Penalties (dangerous zones)")
        form = QFormLayout(box)
        defaults = CostWeights()
        self.alpha = _spin(0, 10, defaults.coastal_penalty, 0.1, 2)
        self.beta = _spin(0, 20, defaults.danger_penalty, 0.5, 2)
        self.radius = _spin(0.5, GraphConfig().land_search_km, defaults.danger_radius_km, 1, 1, " km")
        for widget in (self.alpha, self.beta, self.radius):
            widget.valueChanged.connect(self._weights_edited)
        form.addRow("Coastal water penalty alpha:", self.alpha)
        form.addRow("Danger zone penalty beta:", self.beta)
        form.addRow("Danger zone radius r:", self.radius)
        return box

    def _ga_group(self) -> QGroupBox:
        box = QGroupBox("5. Genetic algorithm")
        form = QFormLayout(box)
        d = GAConfig()
        self.population = _spin(4, 1000, d.population_size, 10)
        self.generations = _spin(1, 5000, d.generations, 50)
        self.crossover = _spin(0, 1, d.crossover_rate, 0.05, 2)
        self.mutation = _spin(0, 1, d.mutation_rate, 0.05, 2)
        self.tournament = _spin(2, 20, d.tournament_size)
        self.elite = _spin(0, 50, d.elite)
        self.stagnation = _spin(0, 5000, d.stagnation_limit, 10)
        self.seed = _spin(0, 999999, d.seed)
        form.addRow("Population size:", self.population)
        form.addRow("Number of generations:", self.generations)
        form.addRow("Crossover probability:", self.crossover)
        form.addRow("Mutation probability:", self.mutation)
        form.addRow("Tournament size:", self.tournament)
        form.addRow("Elite individuals:", self.elite)
        form.addRow("Stop after stagnation (0 = off):", self.stagnation)
        form.addRow("Random seed:", self.seed)
        return box

    def _run_group(self) -> QGroupBox:
        box = QGroupBox("6. Run")
        layout = QVBoxLayout(box)
        row = QHBoxLayout()
        self.run_ga = QPushButton("Genetic algorithm")
        self.run_dijkstra = QPushButton("Dijkstra")
        self.run_astar = QPushButton("A*")
        self.run_ga.clicked.connect(lambda: self.start_runs(["genetic"]))
        self.run_dijkstra.clicked.connect(lambda: self.start_runs(["dijkstra"]))
        self.run_astar.clicked.connect(lambda: self.start_runs(["astar"]))
        for button in (self.run_ga, self.run_dijkstra, self.run_astar):
            row.addWidget(button)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.run_all = QPushButton("Run all and compare")
        self.run_all.clicked.connect(lambda: self.start_runs(["dijkstra", "astar", "genetic"]))
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_task)
        row.addWidget(self.run_all, 1)
        row.addWidget(self.stop_button)
        layout.addLayout(row)
        self.export_button = QPushButton("Export results...")
        self.export_button.clicked.connect(self.export_results)
        layout.addWidget(self.export_button)
        return box

    # ============================================================ parameters
    def graph_config(self) -> GraphConfig:
        return GraphConfig(
            mode="visibility" if self.mode.currentIndex() == 0 else "distance",
            k_neighbours=self.k_neighbours.value(), max_edge_km=self.max_edge.value(),
            sample_step_km=self.sample_step.value(),
        )

    def cost_weights(self) -> CostWeights:
        return CostWeights(self.alpha.value(), self.beta.value(), self.radius.value())

    def ga_config(self) -> GAConfig:
        return GAConfig(
            population_size=self.population.value(), generations=self.generations.value(),
            crossover_rate=self.crossover.value(), mutation_rate=self.mutation.value(),
            tournament_size=self.tournament.value(), elite=self.elite.value(),
            stagnation_limit=self.stagnation.value(), seed=self.seed.value(),
        )

    def endpoints(self):
        return ((self.start_lat.value(), self.start_lon.value()),
                (self.goal_lat.value(), self.goal_lon.value()))

    # ================================================================ events
    def _apply_preset(self, index: int) -> None:
        if index < 0 or index >= len(VOYAGES):
            return
        voyage = VOYAGES[index]
        widgets = (self.start_lat, self.start_lon, self.goal_lat, self.goal_lon)
        for widget in widgets:
            widget.blockSignals(True)
        self.start_lat.setValue(voyage.start[0])
        self.start_lon.setValue(voyage.start[1])
        self.goal_lat.setValue(voyage.goal[0])
        self.goal_lon.setValue(voyage.goal[1])
        for widget in widgets:
            widget.blockSignals(False)
        self._endpoints_edited(from_preset=True)

    def _endpoints_edited(self, *_args, from_preset: bool = False) -> None:
        if not from_preset and self.preset.currentIndex() != len(VOYAGES):
            self.preset.blockSignals(True)
            self.preset.setCurrentIndex(len(VOYAGES))
            self.preset.blockSignals(False)
        start, goal = self.endpoints()
        if self.area.currentText() == AROUND_ROUTE:
            self.graph_dirty = True
        self.session.start, self.session.goal = start, goal
        self.session.runs.clear()
        if not self.graph_dirty and self.session.sea is not None:
            self.session.set_endpoints(start, goal)
        self.update_table()
        self.redraw_map()
        self.redraw_convergence()

    def _graph_edited(self, *_args) -> None:
        self.graph_dirty = True
        self.margin.setEnabled(self.area.currentText() == AROUND_ROUTE)

    def _weights_edited(self, *_args) -> None:
        self.session.set_weights(self.cost_weights())
        self.update_table()
        self.redraw_map()
        self.redraw_convergence()

    def _set_pick_mode(self, mode: Optional[str]) -> None:
        self.pick_mode = mode
        for button, name in ((self.pick_start, "start"), (self.pick_goal, "goal")):
            button.blockSignals(True)
            button.setChecked(mode == name)
            button.blockSignals(False)
        if mode:
            self.statusBar().showMessage(f"Click on the map to place the {'departure' if mode == 'start' else 'destination'}")

    def _on_map_click(self, event) -> None:
        if self.pick_mode is None or event.xdata is None or event.ydata is None:
            return
        if self.map_canvas.toolbar is not None and self.map_canvas.toolbar.mode:
            return                                   # zoom/pan is active
        lat_box, lon_box = ((self.start_lat, self.start_lon) if self.pick_mode == "start"
                            else (self.goal_lat, self.goal_lon))
        lat_box.blockSignals(True)
        lat_box.setValue(event.ydata)
        lat_box.blockSignals(False)
        lon_box.setValue(event.xdata)                # triggers _endpoints_edited
        self._set_pick_mode(None)

    # ================================================================ tasks
    def _set_busy(self, busy: bool) -> None:
        # Everything that changes the session (data, graph, end points, costs)
        # is locked while a background task works on that session.
        for widget in (self.open_button, self.build_button, self.run_ga, self.run_dijkstra,
                       self.run_astar, self.run_all, self.export_button, self.preset,
                       self.area, self.mode, self.start_lat, self.start_lon, self.goal_lat,
                       self.goal_lon, self.pick_start, self.pick_goal, self.alpha, self.beta,
                       self.radius):
            widget.setEnabled(not busy)
        if busy:
            self._set_pick_mode(None)
        self.stop_button.setEnabled(busy)
        if not busy:
            self.progress.setValue(0)

    def _start_thread(self, function: Callable, on_success: Callable) -> None:
        if self.thread is not None and self.thread.isRunning():
            return
        self._set_busy(True)
        thread = TaskThread(function, self)
        thread.progress.connect(self._on_progress)
        thread.generation.connect(self._on_generation)
        thread.succeeded.connect(on_success)
        thread.failed.connect(self._on_failure)
        thread.finished.connect(lambda: self._set_busy(False))
        self.thread = thread
        thread.start()

    def _on_progress(self, message: str, fraction: float) -> None:
        self.statusBar().showMessage(message)
        self.progress.setValue(int(100 * fraction))

    def _on_generation(self, generation: int, best: float, median: float) -> None:
        total = max(1, self.generations.value())
        self.progress.setValue(int(100 * generation / total))
        self.statusBar().showMessage(f"Generation {generation}: best cost {best:.1f}, median {median:.1f}")

    def _on_failure(self, message: str) -> None:
        self.log(message)
        self.statusBar().showMessage("Error - see the Log tab")
        QMessageBox.critical(self, "Error", message.split("\n\n")[0])

    def stop_task(self) -> None:
        if self.thread is not None:
            self.thread.request_stop()

    # ---- dataset
    def _default_dataset(self) -> Optional[Path]:
        for name in ("merged.json", "merged.geojson"):
            path = RAW_DIR / name
            if path.exists():
                return path
        return None

    def choose_dataset(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, "Open labelled dataset", str(RAW_DIR),
            "Point data (*.json *.geojson *.csv);;All files (*)")
        if name:
            self.load_dataset(Path(name))

    def load_dataset(self, path: Path) -> None:
        clean = self.clean_check.isChecked()

        def task(thread: TaskThread):
            thread.progress.emit(f"Reading {path.name}...", 0.1)
            return self.session.load(path, clean=clean)

        def done(summary) -> None:
            self.dataset_label.setText(str(path.name))
            counts = ", ".join(f"{k}: {v}" for k, v in summary.class_counts.items())
            self.dataset_info.setText(f"{summary.n_points} points ({counts}); "
                                      f"{summary.n_conflicts} removed by the depth check")
            self.log(summary.as_text())
            self.graph_dirty = True
            self.session.start, self.session.goal = self.endpoints()
            self.statusBar().showMessage(f"Dataset loaded: {summary.n_points} points")
            self.redraw_map()

        self._start_thread(task, done)

    # ---- graph
    def _graph_task(self, thread: TaskThread) -> None:
        start, goal = self.endpoints()
        self.session.set_weights(self.cost_weights())
        self.session.set_endpoints(start, goal)
        area = None
        if self.area.currentText() != AROUND_ROUTE:
            area = region_bbox(self.area.currentText())
        self.session.build_graph(self.graph_config(), area=area, margin_deg=self.margin.value(),
                                 progress=lambda m, f: thread.progress.emit(m, f))

    def _graph_report(self) -> None:
        sea = self.session.sea
        st = sea.stats
        text = (f"Graph ({sea.config.mode}): {st.n_water_points} nodes, {st.n_edges} edges "
                f"({st.n_removed_by_visibility} candidate edges cross land), mean degree "
                f"{st.mean_degree:.1f}, mean edge {st.mean_edge_km:.1f} km, {st.n_components} components "
                f"(largest {st.largest_component}), built in {st.seconds:.2f} s. "
                f"Departure snapped {self.session.snap_km[0]:.1f} km, destination "
                f"{self.session.snap_km[1]:.1f} km.")
        self.graph_info.setText(text)
        self.log(text)
        if max(self.session.snap_km) > 25:
            self.log("Warning: an end point is far from the nearest graph node - "
                     "the dataset has few water points there.")

    def start_build(self, then: Optional[Callable] = None) -> None:
        if self.session.points is None:
            QMessageBox.information(self, "No dataset", "Open the dataset first.")
            return

        def done(_result) -> None:
            self.graph_dirty = False
            self._graph_report()
            self.update_table()
            self.redraw_map()
            self.redraw_convergence()
            self.statusBar().showMessage("Graph ready")
            if then is not None:
                then()

        self._start_thread(self._graph_task, done)

    # ---- searches
    def start_runs(self, algorithms) -> None:
        if self.session.points is None:
            QMessageBox.information(self, "No dataset", "Open the dataset first.")
            return
        if self.graph_dirty or self.session.sea is None:
            self.start_build(then=lambda: self.start_runs(algorithms))
            return
        ga_config = self.ga_config()
        self.session.set_weights(self.cost_weights())

        def task(thread: TaskThread):
            finished = []
            for name in algorithms:
                if thread.stop_requested():
                    break
                thread.progress.emit(f"Running {ALGORITHM_LABEL[name]}...", 0.0)
                if name == "genetic":
                    self.session.run(name, ga_config,
                                     progress=lambda g, b, m: thread.generation.emit(g, b, m),
                                     should_stop=thread.stop_requested)
                else:
                    self.session.run(name)
                finished.append(name)
            return finished

        def done(finished) -> None:
            for name in finished:
                run = self.session.runs[name]
                r = run.result
                if r.found:
                    self.log(f"{ALGORITHM_LABEL[name]}: cost {r.cost:.2f}, length "
                             f"{run.breakdown['length_km']:.1f} km, {len(r.path)} nodes, "
                             f"effort {r.expanded}, {r.runtime_s:.3f} s. {r.message}")
                else:
                    self.log(f"{ALGORITHM_LABEL[name]}: {r.message}")
            self.update_table()
            self.redraw_map()
            self.redraw_convergence()
            self.statusBar().showMessage("Done")
            if "genetic" in finished and len(finished) == 1:
                self.tabs.setCurrentIndex(1)
            elif len(finished) > 1:
                self.tabs.setCurrentIndex(2)

        self._start_thread(task, done)

    # ================================================================ output
    def redraw_map(self) -> None:
        draw_map(self.map_canvas.figure, self.session, show_edges=self.show_edges.isChecked())
        self.map_canvas.draw_idle()

    def redraw_convergence(self) -> None:
        draw_convergence(self.conv_canvas.figure, self.session)
        self.conv_canvas.draw_idle()

    def update_table(self) -> None:
        rows = self.session.comparison_rows()
        self.table.setRowCount(len(rows))

        def fmt(value, digits=1):
            if value is None or (isinstance(value, float) and not math.isfinite(value)):
                return "-"
            return f"{value:.{digits}f}" if isinstance(value, float) else str(value)

        for i, row in enumerate(rows):
            values = [row["algorithm"], fmt(row["cost"]), fmt(row["length_km"]),
                      fmt(row["coastal_km"]), fmt(row["danger_km"]), fmt(row["min_land_km"], 2),
                      fmt(row["effort"]), fmt(row["runtime_s"], 3), fmt(row["gap_pct"], 2)]
            for j, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, j, item)

    def export_results(self) -> None:
        if not self.session.runs:
            QMessageBox.information(self, "Nothing to export", "Run at least one algorithm first.")
            return
        folder = QFileDialog.getExistingDirectory(self, "Export folder", str(PROJECT_ROOT / "outputs"))
        if not folder:
            return
        files = export_session(self.session, folder, self.map_canvas.figure, self.conv_canvas.figure)
        self.log("Exported:\n" + "\n".join(str(f) for f in files))
        self.statusBar().showMessage(f"{len(files)} files written to {folder}")

    def log(self, text: str) -> None:
        self.log_view.appendPlainText(text)

    def show_about(self) -> None:
        QMessageBox.about(self, "About", f"{APP_TITLE}\n\nCourse project, {APP_AUTHOR}.\n"
                          "Brest State Technical University, Department of Intelligent "
                          "Information Technologies, 2026.")
