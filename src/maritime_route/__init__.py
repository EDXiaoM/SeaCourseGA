"""Sea Course GA - course project: search of a ship's course with a genetic algorithm.

课程设计：基于遗传算法的海船航线搜索。

Sub-packages
------------
:mod:`~maritime_route.pointgraph`
    loading of the labelled points, navigation graph, cost model, Dijkstra and
    A*, the genetic algorithm, session and export (the course project proper);
:mod:`~maritime_route.desktop`
    PyQt5 main window and background threads;
:mod:`~maritime_route.data` and :mod:`~maritime_route.routing.geodesy`
    data loader, cleaning rule and spherical geometry shared with the diploma
    project (https://github.com/EDXiaoM/MaritimeRouteAI).
"""
# Version and author come from config so there is one single source of truth.
# 版本号与作者统一来自 config，避免多处重复定义。
from .config import APP_AUTHOR, APP_VERSION, CLASS_NAMES

#: Package version string (PEP 396 convention), e.g. "1.0.0". 包版本号。
__version__ = APP_VERSION
#: Author of the application. 作者。
__author__ = APP_AUTHOR

# Public names exported by ``from maritime_route import *``. 公开导出的名称。
__all__ = ["__version__", "__author__", "CLASS_NAMES"]
