"""Labelled point set used by the course-project route search.

The course project works directly on the labelled corpus: every point keeps
its WGS-84 coordinates and one of the four zone classes, and no neural network
is involved. This module turns a GeoJSON/CSV/JSON file into a compact
:class:`PointSet` of NumPy arrays and selects the part of it that lies inside
a rectangular area of interest.

Reused parts of the diploma code base
-------------------------------------
* :func:`maritime_route.data.ais_loader.load_any` and
  :func:`~maritime_route.data.ais_loader.validate` read the file and drop rows
  with missing or out-of-range coordinates;
* :func:`maritime_route.data.cleaning.conflict_mask` removes points whose class
  contradicts the measured height or depth (tolerance 5 m);
* :func:`maritime_route.data.cleaning.assign_regions` maps points to the ten
  sea regions of the corpus.

Class codes
-----------
The integer class index is the position in
:data:`~maritime_route.config.CLASS_NAMES`:

=====  ==============  ============================================
index  code            role in the route search
=====  ==============  ============================================
0      OPEN_SEA        graph node, no penalty
1      COASTAL_SEA     graph node, penalised (shallow water)
2      NEAR_COAST      obstacle (land within 5 km of the shore)
3      COASTLINE       obstacle (land remote from the sea)
=====  ==============  ============================================
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..config import CLASS_NAMES, CLASS_TO_INDEX, LABEL_CHECK_TOLERANCE_M, REGIONS
from ..data.ais_loader import DataLoadError, load_any, validate
from ..data.cleaning import assign_regions, conflict_mask

#: Integer indices of the navigable classes (graph nodes).
WATER_INDICES: Tuple[int, ...] = (CLASS_TO_INDEX["OPEN_SEA"], CLASS_TO_INDEX["COASTAL_SEA"])
#: Integer indices of the land classes (obstacles).
LAND_INDICES: Tuple[int, ...] = (CLASS_TO_INDEX["NEAR_COAST"], CLASS_TO_INDEX["COASTLINE"])

#: Bounding box ``(lat_min, lat_max, lon_min, lon_max)`` in degrees.
BBox = Tuple[float, float, float, float]


@dataclass
class LoadSummary:
    """What happened while a point file was read.

    Attributes
    ----------
    source:
        File name.
    n_read:
        Features found in the file.
    n_invalid:
        Rows dropped because of missing or out-of-range coordinates.
    n_unknown_class:
        Rows without one of the four known class codes.
    n_conflicts:
        Rows removed by the label/measurement consistency check.
    n_points:
        Points kept in the :class:`PointSet`.
    class_counts:
        Number of kept points per class code.
    seconds:
        Wall-clock loading time.
    """

    source: str
    n_read: int
    n_invalid: int
    n_unknown_class: int
    n_conflicts: int
    n_points: int
    class_counts: Dict[str, int] = field(default_factory=dict)
    seconds: float = 0.0

    def as_text(self) -> str:
        """Multi-line description for the log window of the GUI."""
        lines = [
            f"File: {self.source}",
            f"Features read: {self.n_read}",
            f"Dropped (invalid coordinates): {self.n_invalid}",
            f"Dropped (unknown class): {self.n_unknown_class}",
            f"Dropped (class contradicts depth/height): {self.n_conflicts}",
            f"Points kept: {self.n_points}",
        ]
        lines += [f"  {name}: {count}" for name, count in self.class_counts.items()]
        lines.append(f"Loading time: {self.seconds:.1f} s")
        return "\n".join(lines)


@dataclass
class PointSet:
    """Labelled points as parallel NumPy arrays.

    Attributes
    ----------
    lat, lon:
        WGS-84 coordinates, decimal degrees, float64.
    cls:
        Class index 0..3 (see the module docstring), int8.
    region:
        Name of the sea region of every point (object array).
    """

    lat: np.ndarray
    lon: np.ndarray
    cls: np.ndarray
    region: np.ndarray

    def __len__(self) -> int:
        return int(self.lat.shape[0])

    def select(self, mask: np.ndarray) -> "PointSet":
        """Subset given by a boolean mask (arrays are copied)."""
        return PointSet(self.lat[mask].copy(), self.lon[mask].copy(),
                        self.cls[mask].copy(), self.region[mask].copy())

    def in_bbox(self, bbox: BBox, margin_deg: float = 0.0) -> np.ndarray:
        """Boolean mask of the points inside ``bbox`` enlarged by ``margin_deg``."""
        lat_min, lat_max, lon_min, lon_max = bbox
        return ((self.lat >= lat_min - margin_deg) & (self.lat <= lat_max + margin_deg)
                & (self.lon >= lon_min - margin_deg) & (self.lon <= lon_max + margin_deg))

    def class_counts(self) -> Dict[str, int]:
        """Number of points per class code, in the order of ``CLASS_NAMES``."""
        counts = np.bincount(self.cls.astype(np.int64), minlength=len(CLASS_NAMES))
        return {name: int(counts[i]) for i, name in enumerate(CLASS_NAMES)}


def load_points(path: Path | str, clean: bool = True,
                tolerance_m: float = LABEL_CHECK_TOLERANCE_M) -> Tuple[PointSet, LoadSummary]:
    """Read a labelled point file into a :class:`PointSet`.

    Parameters
    ----------
    path:
        GeoJSON FeatureCollection (``.geojson``/``.json`` with ``features``),
        CSV or JSON array. Every record needs ``latitude``, ``longitude`` and
        ``class_code``; a GeoJSON point geometry overrides the coordinate
        properties.
    clean:
        Remove points whose class contradicts their measured height/depth.
    tolerance_m:
        Tolerance of that check, metres.

    Returns
    -------
    (PointSet, LoadSummary)

    Raises
    ------
    DataLoadError
        If the file has no usable labelled points.
    """
    t0 = time.perf_counter()
    path = Path(path)
    frame = load_any(path)
    n_read = len(frame)
    frame, _report = validate(frame, source=path.name)
    n_invalid = n_read - len(frame)
    if "class_code" not in frame.columns:
        raise DataLoadError("The file has no 'class_code' attribute - a labelled dataset is required")
    known = frame["class_code"].isin(CLASS_NAMES)
    n_unknown = int((~known).sum())
    frame = frame.loc[known].reset_index(drop=True)
    n_conflicts = 0
    if clean and "noaa_depth" in frame.columns:
        bad = conflict_mask(frame, tolerance_m)
        n_conflicts = int(bad.sum())
        frame = frame.loc[~bad].reset_index(drop=True)
    if frame.empty:
        raise DataLoadError("No labelled points remain after validation")
    points = frame_to_points(frame)
    summary = LoadSummary(
        source=path.name, n_read=n_read, n_invalid=n_invalid,
        n_unknown_class=n_unknown, n_conflicts=n_conflicts, n_points=len(points),
        class_counts=points.class_counts(), seconds=time.perf_counter() - t0,
    )
    return points, summary


def frame_to_points(frame: pd.DataFrame) -> PointSet:
    """Convert a validated, labelled DataFrame into a :class:`PointSet`."""
    lat = frame["latitude"].to_numpy(dtype=np.float64)
    lon = frame["longitude"].to_numpy(dtype=np.float64)
    cls = frame["class_code"].map(CLASS_TO_INDEX).to_numpy(dtype=np.int8)
    region = assign_regions(lat, lon)
    return PointSet(lat, lon, cls, region)


def region_names() -> List[str]:
    """Names of the predefined sea regions of the corpus."""
    return [name for name, _ in REGIONS]


def region_bbox(name: str) -> Optional[BBox]:
    """Bounding box of a predefined region, or ``None`` for an unknown name."""
    for region, box in REGIONS:
        if region == name:
            return box
    return None
