from waam_slicer.klipper_client import KlipperClient
from waam_slicer.config import load_config


# =========================
# LOAD CONFIG
# =========================

cfg = load_config(
    "config.yaml"
)


adaptive_cfg = (
    cfg["adaptive_control"]
)


# =========================
# CONNECT TO KLIPPER
# =========================

client = KlipperClient(

    adaptive_cfg[
        "moonraker_url"
    ],

    timeout=adaptive_cfg.get(
        "request_timeout",
        120
    )
)


print(
    "Connected to:"
)

print(
    adaptive_cfg[
        "moonraker_url"
    ]
)


# =========================
# BUILD TOUCH COMMAND
# =========================

macro = adaptive_cfg[
    "touch_macro"
]

lift = float(
    adaptive_cfg[
        "touch_lift"
    ]
)

probe_speed = float(
    adaptive_cfg[
        "probe_speed"
    ]
)


command = (
    f"{macro} "
    f"LIFT={lift} "
    f"SPEED={probe_speed}"
)


print(
    f"Sending command: "
    f"{command}"
)


# =========================
# RUN TOUCH
# =========================

client.run_gcode(
    command
)


print(
    "Touch completed."
)


# =========================
# READ PTOUCH
# =========================

position = (
    client
    .get_last_probe_position()
)


p_touch = position["z"]


print(
    f"pTouch X = "
    f"{position['x']:.4f} mm"
)

print(
    f"pTouch Y = "
    f"{position['y']:.4f} mm"
)

print(
    f"pTouch Z = "
    f"{position['z']:.4f} mm"
)


# =========================
# CALCULATE NEXT Z
# =========================

H = float(
    cfg["slicing"]
    ["layer_height_H"]
)


correction = float(
    adaptive_cfg.get(
        "z_correction_offset",
        0.0
    )
)


next_z = (
    p_touch
    + H
    + correction
)


print("")
print(
    "Next layer calculation:"
)

print(
    f"pTouch = "
    f"{p_touch:.4f} mm"
)

print(
    f"H      = "
    f"{H:.4f} mm"
)

print(
    f"Correction = "
    f"{correction:.4f} mm"
)

print(
    "------------------------"
)

print(
    f"Next Z = "
    f"{next_z:.4f} mm"
)