from dataclasses import dataclass
import numpy as np
from shapely.geometry import Polygon


@dataclass
class RingRecord:
    polygon: Polygon
    parent: int | None = None
    depth: int = 0


def _closed_xy(loop_xyz):
    xy = np.asarray(loop_xyz, dtype=float)[:, :2]
    if len(xy) >= 3 and not np.allclose(xy[0], xy[-1]):
        xy = np.vstack([xy, xy[0]])
    return xy


def section_loops_to_polygons(discrete_loops, min_area=0.2):
    rings = []
    for loop in discrete_loops:
        xy = _closed_xy(loop)
        if len(xy) < 4:
            continue
        poly = Polygon(xy)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.geom_type == 'Polygon' and poly.area >= min_area:
            rings.append(RingRecord(poly))
        elif poly.geom_type == 'MultiPolygon':
            rings.extend(RingRecord(p) for p in poly.geoms if p.area >= min_area)

    if not rings:
        return []

    order = sorted(range(len(rings)), key=lambda i: rings[i].polygon.area, reverse=True)
    for pos, child_idx in enumerate(order):
        child = rings[child_idx].polygon
        probe = child.representative_point()
        parent_idx = None
        parent_area = float('inf')
        for candidate_idx in order[:pos]:
            candidate = rings[candidate_idx].polygon
            if candidate.area < parent_area and candidate.contains(probe):
                parent_idx = candidate_idx
                parent_area = candidate.area
        rings[child_idx].parent = parent_idx

    def depth_of(idx):
        d = 0
        p = rings[idx].parent
        while p is not None:
            d += 1
            p = rings[p].parent
        return d

    for i in range(len(rings)):
        rings[i].depth = depth_of(i)

    output = []
    for i, ring in enumerate(rings):
        if ring.depth % 2 != 0:
            continue
        holes = [
            list(child.polygon.exterior.coords)
            for child in rings
            if child.parent == i and child.depth == ring.depth + 1
        ]
        result = Polygon(list(ring.polygon.exterior.coords), holes=holes)
        if not result.is_valid:
            result = result.buffer(0)
        if result.geom_type == 'Polygon' and result.area >= min_area:
            output.append(result)
        elif result.geom_type == 'MultiPolygon':
            output.extend(p for p in result.geoms if p.area >= min_area)
    return output
