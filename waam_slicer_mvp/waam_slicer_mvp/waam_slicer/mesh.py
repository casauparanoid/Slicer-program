from pathlib import Path
import trimesh


def load_mesh(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'Mesh not found: {path}')

    loaded = trimesh.load(path, force='mesh')
    if isinstance(loaded, trimesh.Scene):
        if not loaded.geometry:
            raise ValueError('Scene contains no geometry.')
        mesh = trimesh.util.concatenate(tuple(loaded.geometry.values()))
    else:
        mesh = loaded

    if mesh.is_empty:
        raise ValueError('Mesh is empty.')
    mesh.remove_unreferenced_vertices()
    return mesh
