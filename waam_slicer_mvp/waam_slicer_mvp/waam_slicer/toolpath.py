from dataclasses import dataclass
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry.polygon import orient


@dataclass
class ToolpathPoint:
    layer_id: int
    polygon_id: int
    offset_index: int
    ring_type: str
    point_id: int
    x: float
    y: float
    z: float
    status: str


def _as_polygon_list(geom):
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return []


def _force_ring_direction(coords, direction):
    poly = Polygon(coords)
    poly = orient(poly, sign=-1.0 if direction == 'CW' else 1.0)
    return list(poly.exterior.coords)


def _direction_for_path(index, mode):
    if mode == 'CW':
        return 'CW'
    if mode == 'CCW':
        return 'CCW'
    return 'CW' if index % 2 == 0 else 'CCW'


def _transform_xyz(x, y, z, cfg):
    cad = cfg['coordinate_system']['cad_origin']
    machine = cfg['coordinate_system']['machine_origin']
    return (
        x - float(cad[0]) + float(machine[0]),
        y - float(cad[1]) + float(machine[1]),
        z - float(cad[2]) + float(machine[2]),
    )


def _emit_ring(coords, layer_id, polygon_id, offset_index, ring_type, z, direction, cfg):
    coords = _force_ring_direction(coords, direction)
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    out = []
    for i, (x, y) in enumerate(coords):
        if i == 0:
            status = 'ARC_START'
        elif i == len(coords) - 1:
            status = 'ARC_STOP'
        else:
            status = 'IDLE'

        x, y, zt = _transform_xyz(float(x), float(y), float(z), cfg)
        out.append(ToolpathPoint(
            layer_id, polygon_id, offset_index, ring_type,
            i, x, y, zt, status
        ))
    return out


def build_toolpath(layers, cfg):
    W = float(cfg['toolpath']['bead_width_W'])
    d = float(cfg['toolpath']['offset_factor']) * W
    min_area = float(cfg['toolpath'].get('min_polygon_area', 0.2))
    tol = float(cfg['toolpath'].get('simplify_tolerance', 0.01))
    mode = cfg['toolpath']['contour_direction']

    all_points = []
    polygon_id = 0
    global_path_index = 0

    for layer in layers:
        current = [p for p in layer.polygons if p.area >= min_area]
        offset_index = 0

        while current:
            next_generation = []
            for poly in current:
                if tol > 0:
                    poly = poly.simplify(tol, preserve_topology=True)
                if poly.is_empty or poly.area < min_area:
                    continue

                direction = _direction_for_path(global_path_index, mode)
                all_points.extend(_emit_ring(
                    poly.exterior.coords, layer.layer_id, polygon_id,
                    offset_index, 'EXTERIOR', layer.z, direction, cfg
                ))
                polygon_id += 1
                global_path_index += 1

                for interior in poly.interiors:
                    direction = _direction_for_path(global_path_index, mode)
                    all_points.extend(_emit_ring(
                        interior.coords, layer.layer_id, polygon_id,
                        offset_index, 'HOLE', layer.z, direction, cfg
                    ))
                    polygon_id += 1
                    global_path_index += 1

                shrunken = poly.buffer(-d, join_style='round')
                next_generation.extend(
                    p for p in _as_polygon_list(shrunken) if p.area >= min_area
                )

            current = next_generation
            offset_index += 1
    return all_points
