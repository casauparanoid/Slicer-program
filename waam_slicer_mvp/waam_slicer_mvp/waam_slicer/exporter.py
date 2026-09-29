import csv
from pathlib import Path

FIELDS = [
    'layer_id', 'polygon_id', 'offset_index', 'ring_type',
    'point_id', 'x', 'y', 'z', 'status'
]


def export_csv(points, cfg):
    path = Path(cfg['export']['csv_path'])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for p in points:
            writer.writerow({
                'layer_id': p.layer_id,
                'polygon_id': p.polygon_id,
                'offset_index': p.offset_index,
                'ring_type': p.ring_type,
                'point_id': p.point_id,
                'x': f'{p.x:.6f}',
                'y': f'{p.y:.6f}',
                'z': f'{p.z:.6f}',
                'status': p.status,
            })
    return path
