# WAAM Slicer MVP — Python / Trimesh / Shapely

Simple 3-axis WAAM slicer based on the supervisor's proposed workflow:

```text
CAD/STL
  -> Trimesh
  -> slicing at zk = z_min + kH
  -> Shapely closed polygons
  -> external contour
  -> repeated inward offsets d = 0.737W
  -> ordered X,Y points
  -> fixed/alternating contour direction
  -> add Z
  -> transform to machine origin
  -> ARC_START / IDLE / ARC_STOP
  -> CSV
  -> optional G-code
```

## Install

```bash
python -m venv .venv
```

Windows:

```bash
.venv\\Scripts\\activate
pip install -r requirements.txt
```

## Quick test

```bash
python examples/generate_sample_stl.py
python main.py --stl examples/sample_box.stl --config config.yaml
```

Generated files:

```text
output/toolpath.csv
output/toolpath.gcode
output/layers/layer_XXXX.png
```

## Main equations

```text
zk = z_min + kH
d  = 0.737W
```

`H` and `W` are manually entered in this MVP. A later AI module can estimate them from wire material and WAAM process parameters.

## CSV status

- first point: `ARC_START`
- intermediate points: `IDLE`
- final closing point: `ARC_STOP`

`IDLE` means no new torch command is sent. The arc stays ON between `ARC_START` and `ARC_STOP`.

## Direction constraint

The default is:

```yaml
contour_direction: CW
```

This forces every closed contour to use the same circulation direction. Change to `CCW` or `ALTERNATE` if the hardware later supports it.

Important: if the hardware can deposit only in a fixed Cartesian direction such as `+X`, closed contour paths are physically incompatible with that constraint. Then the strategy should be changed to open unidirectional passes.
