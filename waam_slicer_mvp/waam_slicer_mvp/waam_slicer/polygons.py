from dataclasses import dataclass
import numpy as np
from shapely.geometry import Polygon


@dataclass
class RingRecord:
    # Track a ring, its parent index in rings, and its nesting depth.
    polygon: Polygon
    parent: int | None = None
    depth: int = 0


def _closed_xy(loop_xyz):
    # Horizontal slice loops share one Z value; only XY is needed here.
    xy = np.asarray(loop_xyz, dtype=float)[:, :2]
    # Repeat the first point to close the ring unless endpoints are already close.
    if len(xy) >= 3 and not np.allclose(xy[0], xy[-1]):
        xy = np.vstack([xy, xy[0]])
    return xy


def section_loops_to_polygons(discrete_loops, min_area=0.2):
    # Convert section loops into filled rings before classifying shells and holes.
    # min_area uses squared input units and filters both rings and final regions.
    rings = []
    for loop in discrete_loops:
        xy = _closed_xy(loop)
        # A closed triangle needs three vertices plus the repeated start point.
        if len(xy) < 4:
            continue
        poly = Polygon(xy)
        # A zero-width buffer can repair invalid geometry or split it into parts.
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.geom_type == 'Polygon' and poly.area >= min_area:
            rings.append(RingRecord(poly))
        elif poly.geom_type == 'MultiPolygon':
            rings.extend(RingRecord(p) for p in poly.geoms if p.area >= min_area)

    if not rings:
        return []

    # Larger rings come first so possible parents precede their children.
    order = sorted(range(len(rings)), key=lambda i: rings[i].polygon.area, reverse=True)
    for pos, child_idx in enumerate(order):
        child = rings[child_idx].polygon
        # Use an interior point; a centroid can lie outside a concave polygon.
        # This containment heuristic assumes nested, non-crossing section rings.
        probe = child.representative_point()
        parent_idx = None
        parent_area = float('inf')
        # Choose the smallest preceding ring containing the probe as the parent.
        for candidate_idx in order[:pos]:
            candidate = rings[candidate_idx].polygon
            if candidate.area < parent_area and candidate.contains(probe):
                parent_idx = candidate_idx
                parent_area = candidate.area
        rings[child_idx].parent = parent_idx

    # Count ancestors: outer shell = 0, hole = 1, island inside a hole = 2, etc.
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
        # Even depths are material regions; odd depths become holes in a parent.
        if ring.depth % 2 != 0:
            continue
        # Attach only immediate children as holes; deeper islands are emitted
        # separately when their own even-depth ring is processed.
        holes = [
            list(child.polygon.exterior.coords)
            for child in rings
            if child.parent == i and child.depth == ring.depth + 1
        ]
        result = Polygon(list(ring.polygon.exterior.coords), holes=holes)
        # Repair the assembled shell/holes and filter its remaining material area.
        if not result.is_valid:
            result = result.buffer(0)
        if result.geom_type == 'Polygon' and result.area >= min_area:
            output.append(result)
        elif result.geom_type == 'MultiPolygon':
            output.extend(p for p in result.geoms if p.area >= min_area)
    return output
