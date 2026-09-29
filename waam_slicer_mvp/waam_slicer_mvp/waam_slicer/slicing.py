from dataclasses import dataclass
import trimesh
from .polygons import section_loops_to_polygons


@dataclass
class SliceLayer:
    layer_id: int
    z: float
    polygons: list


def build_slices(mesh: trimesh.Trimesh, cfg):
    z_first = float(cfg['slicing']['z_min'])
    H = float(cfg['slicing']['layer_height_H'])
    min_area = float(cfg['toolpath'].get('min_polygon_area', 0.2))

    mesh_z_min = float(mesh.bounds[0, 2])
    mesh_z_max = float(mesh.bounds[1, 2])
    first_plane = mesh_z_min + z_first

    layers = []
    k = 0
    while True:
        z = first_plane + k * H
        if z > mesh_z_max + 1e-9:
            break

        section = mesh.section(
            plane_origin=[0.0, 0.0, z],
            plane_normal=[0.0, 0.0, 1.0],
        )
        if section is not None:
            polygons = section_loops_to_polygons(section.discrete, min_area)
            if polygons:
                layers.append(SliceLayer(len(layers), float(z), polygons))
        k += 1
    return layers
