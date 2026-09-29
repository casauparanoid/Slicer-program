from tkinter import Tk, filedialog

from waam_slicer.config import load_config
from waam_slicer.mesh import load_mesh
from waam_slicer.slicing import build_slices
from waam_slicer.toolpath import build_toolpath
from waam_slicer.exporter import export_csv
from waam_slicer.visualize import save_layer_previews
from waam_slicer.gcode import export_gcode


def select_stl_file():
    root = Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="Select STL model",
        filetypes=[
            ("STL files", "*.stl"),
            ("All files", "*.*")
        ]
    )

    root.destroy()

    return file_path


def main():
    # Load configuration
    cfg = load_config("config.yaml")

    # Select STL file
    stl_path = select_stl_file()

    if not stl_path:
        print("No STL file selected.")
        return

    print(f"Selected model: {stl_path}")

    # Load mesh
    mesh = load_mesh(stl_path)

    # Print model dimensions
    size = mesh.extents

    print(
        f"Model size: "
        f"X={size[0]:.2f} mm, "
        f"Y={size[1]:.2f} mm, "
        f"Z={size[2]:.2f} mm"
    )

    print("[1/5] Mesh loaded")

    # Generate slices
    layers = build_slices(mesh, cfg)

    if not layers:
        raise RuntimeError("No valid slices were generated.")

    print(f"[2/5] Generated {len(layers)} valid slice(s)")

    # Generate toolpath
    points = build_toolpath(layers, cfg)

    if not points:
        raise RuntimeError("No toolpath points were generated.")

    # Export CSV
    csv_path = export_csv(points, cfg)

    print(f"[3/5] CSV: {csv_path}")

    # Save layer images
    image_dir = save_layer_previews(
        layers,
        points,
        cfg
    )

    print(f"[4/5] Layer images: {image_dir}")

    # Export G-code
    gcode_path = export_gcode(
        points,
        cfg
    )

    print(f"[5/5] G-code: {gcode_path}")

    print("Done.")


if __name__ == "__main__":
    main()