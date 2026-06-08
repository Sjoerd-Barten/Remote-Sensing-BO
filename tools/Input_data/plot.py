import math
import numpy as np
import pandas as pd
from typing import Literal

PointType = Literal["center", "top_left", "top_right", "bottom_right", "bottom_left"]
VALID_POINT_TYPES = ("center", "top_left", "top_right", "bottom_right", "bottom_left")

def rotate_point(x, y, cx, cy, angle_rad):
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    dx = x - cx
    dy = y - cy

    rx = cx + dx * cos_a - dy * sin_a
    ry = cy + dx * sin_a + dy * cos_a

    return rx, ry

def generate_rectangle_corners(
    x,
    y,
    width,
    height,
    rotation_deg=0,
    point_type: PointType = "center"
):
    if point_type not in VALID_POINT_TYPES:
        raise ValueError(f"point_type moet één van deze waarden zijn: {VALID_POINT_TYPES}")

    if width <= 0 or height <= 0:
        raise ValueError("width en height moeten groter zijn dan 0")

    angle = np.radians(rotation_deg)
    cos_a = np.cos(angle)
    sin_a = np.sin(angle)

    local = {
        "top_left": (-width / 2, height / 2),
        "top_right": (width / 2, height / 2),
        "bottom_right": (width / 2, -height / 2),
        "bottom_left": (-width / 2, -height / 2),
    }

    def rotate(dx, dy):
        rx = dx * cos_a - dy * sin_a
        ry = dx * sin_a + dy * cos_a
        return rx, ry

    if point_type == "center":
        cx, cy = x, y
    else:
        dx, dy = local[point_type]
        rdx, rdy = rotate(dx, dy)
        cx = x - rdx
        cy = y - rdy

    corners = {}
    for name, (dx, dy) in local.items():
        rdx, rdy = rotate(dx, dy)
        corners[name] = (cx + rdx, cy + rdy)

    return corners


def corners_to_columns(
    row,
    x_col="X",
    y_col="Y",
    width=10,
    height=10,
    rotation_deg=0,
    point_type="center"
):
    if x_col not in row.index:
        raise KeyError(f"Kolom '{x_col}' bestaat niet in de DataFrame")
    if y_col not in row.index:
        raise KeyError(f"Kolom '{y_col}' bestaat niet in de DataFrame")

    corners = generate_rectangle_corners(
        x=row[x_col],
        y=row[y_col],
        width=width,
        height=height,
        rotation_deg=rotation_deg,
        point_type=point_type,
    )

    return pd.Series({
        "x_tl": corners["top_left"][0],
        "y_tl": corners["top_left"][1],
        "x_tr": corners["top_right"][0],
        "y_tr": corners["top_right"][1],
        "x_br": corners["bottom_right"][0],
        "y_br": corners["bottom_right"][1],
        "x_bl": corners["bottom_left"][0],
        "y_bl": corners["bottom_left"][1],
    })