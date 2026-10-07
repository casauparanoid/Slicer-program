from pathlib import Path
import warnings

import numpy as np
import trimesh


def _validate_geometry(mesh):
    """Reject malformed geometry before indexing vertices or cleaning faces."""
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError('Expected a triangle mesh, not points or curves.')

    vertices = mesh.vertices
    faces = mesh.faces
    if len(vertices) == 0 or len(faces) == 0:
        raise ValueError('Mesh is empty or contains no triangle faces.')
    if vertices.ndim != 2 or vertices.shape[1] != 3:
        raise ValueError('Mesh vertices must have three coordinates each.')
    if faces.ndim != 2 or faces.shape[1] != 3:
        raise ValueError('Mesh faces must contain three vertex indices each.')
    if not np.isfinite(vertices).all():
        raise ValueError('Mesh contains NaN or infinite vertex coordinates.')
    if np.any(faces < 0) or np.any(faces >= len(vertices)):
        raise ValueError('Mesh contains face indices outside the vertex array.')


def _scene_to_mesh(scene):
    """Flatten scene instances while preserving their world transforms."""
    parts = []
    # Walk instances, not just geometry.values(): one mesh may be used by
    # several nodes with different positions, rotations, or scales.
    for node in scene.graph.nodes_geometry:
        transform, geometry_name = scene.graph[node]
        geometry = scene.geometry[geometry_name]
        _validate_geometry(geometry)
        if not np.isfinite(transform).all():
            raise ValueError(f'Scene node {node!r} has an invalid transform.')
        part = geometry.copy()
        part.apply_transform(transform)
        parts.append(part)

    if not parts:
        raise ValueError('Scene contains no mesh instances.')
    return trimesh.util.concatenate(parts)


def load_mesh(path, *, require_watertight=True):
    """Load and clean a mesh without filling holes or moving its geometry.

    By default, reject open or non-manifold edges because downstream slicing
    expects closed material boundaries. Designed through-holes are allowed
    when their walls form a closed surface. Set require_watertight=False only
    to inspect an open mesh; a warning is still emitted.

    These checks do not detect every self-intersection or overlapping solid.
    File units and coordinates are preserved; no automatic scaling is applied.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'Mesh not found: {path}')
    if not path.is_file():
        raise ValueError(f'Mesh path is not a file: {path}')

    # Disable automatic processing so invalid coordinates are not silently
    # discarded and nearby vertices are not merged across narrow features.
    loaded = trimesh.load(path, process=False)
    mesh = _scene_to_mesh(loaded) if isinstance(loaded, trimesh.Scene) else loaded
    _validate_geometry(mesh)

    # STL files commonly repeat vertices for every triangle. Merge only exact
    # duplicates, preserving small gaps and every retained vertex coordinate.
    _, unique_indices, inverse = np.unique(
        mesh.vertices, axis=0, return_index=True, return_inverse=True
    )
    mesh.update_vertices(unique_indices, inverse=inverse)

    # Remove duplicate faces (including reversed copies) and zero-area faces.
    # Do not filter by a minimum area: small faces may describe designed holes.
    areas = mesh.area_faces
    if not np.isfinite(areas).all():
        raise ValueError('Mesh face areas are not finite; check coordinate scale.')
    _, unique_faces = np.unique(
        np.sort(mesh.faces, axis=1), axis=0, return_index=True
    )
    keep = np.zeros(len(mesh.faces), dtype=bool)
    keep[unique_faces] = True
    keep &= areas > 0.0
    removed_count = int((~keep).sum())
    mesh.update_faces(keep)
    mesh.remove_unreferenced_vertices()
    _validate_geometry(mesh)
    if removed_count:
        warnings.warn(
            f'Removed {removed_count} duplicate or zero-area face(s) from {path.name}.',
            UserWarning,
            stacklevel=2,
        )

    # A closed surface may contain intentional tunnels or cavities. Never fill
    # holes or replace the mesh with a convex hull to make this check pass.
    if not mesh.is_watertight:
        _, edge_counts = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
        boundary_edges = int((edge_counts == 1).sum())
        non_manifold_edges = int((edge_counts > 2).sum())
        message = (
            f'Mesh is not watertight: {boundary_edges} boundary edge(s), '
            f'{non_manifold_edges} non-manifold edge(s). '
            'Repair the source mesh before generating closed slicing contours.'
        )
        if require_watertight:
            raise ValueError(message)
        warnings.warn(message, UserWarning, stacklevel=2)

    # Report inconsistent winding without flipping disconnected cavity shells,
    # whose inward orientation may be intentional.
    if not mesh.is_winding_consistent:
        warnings.warn(
            'Mesh has inconsistent face winding; inspect face orientation.',
            UserWarning,
            stacklevel=2,
        )
    return mesh
