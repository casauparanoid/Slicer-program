from pathlib import Path
import yaml


def load_config(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'Configuration file not found: {path}')
    with path.open('r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    direction = str(cfg['toolpath'].get('contour_direction', 'CW')).upper()
    if direction not in {'CW', 'CCW', 'ALTERNATE'}:
        raise ValueError('contour_direction must be CW, CCW, or ALTERNATE')
    cfg['toolpath']['contour_direction'] = direction

    if float(cfg['slicing']['layer_height_H']) <= 0:
        raise ValueError('layer_height_H must be > 0')
    if float(cfg['toolpath']['bead_width_W']) <= 0:
        raise ValueError('bead_width_W must be > 0')
    if float(cfg['toolpath']['offset_factor']) <= 0:
        raise ValueError('offset_factor must be > 0')
    return cfg
