from collections import defaultdict
from pathlib import Path
import matplotlib.pyplot as plt


def save_layer_previews(layers, points, cfg):
    image_dir = Path(cfg['export']['image_dir'])
    image_dir.mkdir(parents=True, exist_ok=True)

    by_layer = defaultdict(list)
    for p in points:
        by_layer[p.layer_id].append(p)

    for layer in layers:
        fig, ax = plt.subplots(figsize=(7, 7))

        for poly in layer.polygons:
            x, y = poly.exterior.xy
            ax.plot(x, y, linewidth=1)
            for hole in poly.interiors:
                hx, hy = hole.xy
                ax.plot(hx, hy, linewidth=1)

        grouped = defaultdict(list)
        for p in by_layer[layer.layer_id]:
            grouped[p.polygon_id].append(p)
        for pts in grouped.values():
            pts.sort(key=lambda p: p.point_id)
            ax.plot([p.x for p in pts], [p.y for p in pts], linewidth=0.8)

        ax.set_aspect('equal', adjustable='box')
        ax.set_title(f'Layer {layer.layer_id} | Z={layer.z:.3f} mm')
        ax.set_xlabel('X [mm]')
        ax.set_ylabel('Y [mm]')
        ax.grid(True, linewidth=0.3)
        fig.tight_layout()
        fig.savefig(image_dir / f'layer_{layer.layer_id:04d}.png', dpi=160)
        plt.close(fig)

    return image_dir
