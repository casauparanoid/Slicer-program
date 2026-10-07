from dataclasses import dataclass
import trimesh
from .polygons import section_loops_to_polygons


@dataclass
class SliceLayer:
    # Store one valid slice: its sequential ID, CAD Z height, and 2D polygons.
    layer_id: int
    z: float
    polygons: list


def build_slices(mesh: trimesh.Trimesh, cfg):
    # z_min is an offset above the mesh bottom, not an absolute Z coordinate.
    z_first = float(cfg['slicing']['z_min'])
    # H is the vertical spacing between consecutive cutting planes.
    H = float(cfg['slicing']['layer_height_H'])
    # Pass the minimum accepted ring/polygon area to the polygon conversion.
    min_area = float(cfg['toolpath'].get('min_polygon_area', 0.2))

    # Use the mesh bounds to position the first plane and limit the slice range.
    mesh_z_min = float(mesh.bounds[0, 2])
    mesh_z_max = float(mesh.bounds[1, 2])
    first_plane = mesh_z_min + z_first

    layers = []
    k = 0
    while True:
        # Compute each height from its index to avoid accumulating step errors.
        z = first_plane + k * H
        # Allow a small numerical tolerance at the mesh's upper Z boundary.
        if z > mesh_z_max + 1e-9:
            break

        # Intersect the mesh with a horizontal plane whose normal is the Z axis.
        section = mesh.section(
            plane_origin=[0.0, 0.0, z],
            plane_normal=[0.0, 0.0, 1.0],
        )
        if section is not None:
            # Convert the 3D intersection loops to XY polygons, including holes.
            polygons = section_loops_to_polygons(section.discrete, min_area)
            if polygons:
                # Number only retained slices; skipped planes do not leave ID gaps.
                layers.append(SliceLayer(len(layers), float(z), polygons))
        # Advance even if this plane has no intersection or no accepted polygons.
        k += 1
    return layers
