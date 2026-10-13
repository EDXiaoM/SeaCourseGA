"""Data access layer: loading, validation and feature engineering.

数据访问层：加载、校验与特征工程。

Modules
-------
:mod:`~maritime_route.data.ais_loader`
    Reads GeoJSON / CSV / JSON point files into a :class:`pandas.DataFrame`,
    normalises column names and drops rows with invalid coordinates.
:mod:`~maritime_route.data.cleaning`
    Removes labelled points whose class contradicts their measured
    height/depth, and assigns every point to one of the ten sea regions.
:mod:`~maritime_route.data.features`
    Builds the label-free :class:`ReferenceIndex` and the 28-column feature
    matrix that is the input of the neural network.
The course project uses the loader and the cleaning rule
(:mod:`maritime_route.pointgraph.dataset`); both modules are shared with the
diploma project.

子模块：ais_loader（读取与校验）、cleaning（清洗与海域划分）、features（参考索引
与 28 维特征）。课程设计使用其中的读取与清洗功能（与毕业设计共用）。
"""
# Re-export the public API so callers can write ``from maritime_route.data import ...``.
# 重新导出公共接口，便于上层直接从 maritime_route.data 导入。
from .ais_loader import DataLoadError, LoadReport, load_any, load_geojson, validate
from .features import FEATURE_NAMES, N_FEATURES, ReferenceIndex, build_features, features_for_coordinates

__all__ = [
    "DataLoadError", "LoadReport", "load_any", "load_geojson", "validate",
    "FEATURE_NAMES", "N_FEATURES", "ReferenceIndex", "build_features",
    "features_for_coordinates",
]
