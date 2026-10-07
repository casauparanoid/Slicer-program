from dataclasses import dataclass
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry.polygon import orient


@dataclass
class ToolpathPoint:
    # One vertex of a closed deposition path, expressed in machine coordinates.
    layer_id: int
    # Despite the name, polygon_id identifies each emitted ring/path globally.
    polygon_id: int
    # Offset generation within the layer: 0 is the original polygon boundary.
    offset_index: int
    ring_type: str
    point_id: int
    x: float
    y: float
    z: float
    status: str


def _as_polygon_list(geom):
    # Inward buffering can remove a region or split it into several polygons.
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return []


def _force_ring_direction(coords, direction):
    # Treat this ring as an exterior to enforce CW/CCW for shells and holes alike.
    # Shapely uses a negative orientation sign for CW and a positive one for CCW.
    poly = Polygon(coords)
    poly = orient(poly, sign=-1.0 if direction == 'CW' else 1.0)
    return list(poly.exterior.coords)


def _direction_for_path(index, mode):
    # ALTERNATE switches direction per emitted ring, including across layers.
    if mode == 'CW':
        return 'CW'
    if mode == 'CCW':
        return 'CCW'
    return 'CW' if index % 2 == 0 else 'CCW'


def _transform_xyz(x, y, z, cfg):
    # Translate CAD coordinates to machine coordinates; no rotation or scaling.
    cad = cfg['coordinate_system']['cad_origin']
    machine = cfg['coordinate_system']['machine_origin']
    return (
        x - float(cad[0]) + float(machine[0]),
        y - float(cad[1]) + float(machine[1]),
        z - float(cad[2]) + float(machine[2]),
    )


def _emit_ring(coords, layer_id, polygon_id, offset_index, ring_type, z, direction, cfg):
    # Order and close the XY ring before adding the layer height to every vertex.
    coords = _force_ring_direction(coords, direction)
    # Repeat the start vertex so the final deposition segment closes the loop.
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    out = []
    for i, (x, y) in enumerate(coords):
        # Mark arc events at the ends; IDLE means no state change, not arc off.
        if i == 0:
            status = 'ARC_START'
        elif i == len(coords) - 1:
            status = 'ARC_STOP'
        else:
            status = 'IDLE'

        # All vertices in this ring share the same CAD Z, then receive the origin shift.
        x, y, zt = _transform_xyz(float(x), float(y), float(z), cfg)
        out.append(ToolpathPoint(
            layer_id, polygon_id, offset_index, ring_type,
            i, x, y, zt, status
        ))
    return out


def build_toolpath(layers, cfg):
    W = float(cfg['toolpath']['bead_width_W'])
    # Distance between successive inward offsets; W is the nominal bead width.
    d = float(cfg['toolpath']['offset_factor']) * W
    min_area = float(cfg['toolpath'].get('min_polygon_area', 0.2))
    tol = float(cfg['toolpath'].get('simplify_tolerance', 0.01))
    mode = cfg['toolpath']['contour_direction']

    all_points = []
    polygon_id = 0
    global_path_index = 0

    # Process each slice independently, retaining its height and layer ID.
    for layer in layers:
        current = [p for p in layer.polygons if p.area >= min_area]
        offset_index = 0

        # Emit the current boundaries, then erode the remaining material region.
        # Stop when no polygons survive the offset and minimum-area filtering.
        while current:
            next_generation = []
            for poly in current:
                # Reduce vertex count while preserving the polygon topology.
                if tol > 0:
                    poly = poly.simplify(tol, preserve_topology=True)
                if poly.is_empty or poly.area < min_area:
                    continue

                direction = _direction_for_path(global_path_index, mode)
                # Generation 0 follows the original boundary: no W/2 inset is applied.
                all_points.extend(_emit_ring(
                    poly.exterior.coords, layer.layer_id, polygon_id,
                    offset_index, 'EXTERIOR', layer.z, direction, cfg
                ))
                polygon_id += 1
                global_path_index += 1

                # Hole boundaries are separate closed deposition paths, each with its own ID.
                for interior in poly.interiors:
                    direction = _direction_for_path(global_path_index, mode)
                    all_points.extend(_emit_ring(
                        interior.coords, layer.layer_id, polygon_id,
                        offset_index, 'HOLE', layer.z, direction, cfg
                    ))
                    polygon_id += 1
                    global_path_index += 1

                # A negative buffer moves the outer boundary inward and hole boundaries
                # outward, reducing material from both sides; corners use round joins.
                shrunken = poly.buffer(-d, join_style='round')
                next_generation.extend(
                    p for p in _as_polygon_list(shrunken) if p.area >= min_area
                )

            # Keep every surviving component if erosion splits a polygon.
            current = next_generation
            offset_index += 1
    # Flat vertex list; consecutive points within one path define 3D line segments.
    # Travel between paths and G-code commands are handled by the exporter.
    return all_points
