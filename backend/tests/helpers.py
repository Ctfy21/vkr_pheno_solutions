"""Synthetic plant images with known geometry for algorithm and pipeline tests."""
import io
from typing import Optional

import numpy as np
from PIL import Image

PLANT_GREEN = (40, 160, 40)  # RGB, inside the HSV range of the segmentation


def plant_image(
    height_px: int = 200,
    width_px: int = 60,
    canvas=(400, 600),
    fmt: str = "PNG",
    exif_time: Optional[str] = None,
    offset: Optional[str] = None,
    seed_color: int = 0,
) -> bytes:
    """
    White canvas (width x height) with a green rectangular 'plant' standing on the
    bottom part of the frame, left of the ruler zone that the algorithm masks out.
    With scale 10 px/cm: height = height_px / 10 cm, area = height_px * width_px / 100 cm².
    """
    w, h = canvas
    arr = np.full((h, w, 3), 255, dtype=np.uint8)
    arr[0, 0] = (255, 255, 255 - seed_color % 50)  # makes files with equal geometry distinct
    bottom = h - 50
    left = 60
    arr[bottom - height_px:bottom, left:left + width_px] = PLANT_GREEN
    img = Image.fromarray(arr, "RGB")
    buf = io.BytesIO()
    if exif_time:
        exif = Image.Exif()
        exif[271] = "PhenoCam"
        exif[272] = "Test-1"
        sub = {36867: exif_time}
        if offset:
            sub[36881] = offset
        exif[0x8769] = sub
        img.save(buf, "JPEG", quality=95, exif=exif)
    else:
        img.save(buf, fmt, **({"quality": 95} if fmt == "JPEG" else {}))
    return buf.getvalue()


def _png(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr[:, :, ::-1].copy(), "RGB").save(buf, "PNG")  # BGR -> RGB
    return buf.getvalue()


def ruler_scene(px_per_cm: float = 10.0, labels=range(10, 80, 10), leaf_blobs: bool = True) -> bytes:
    """
    White wall with a ruler on the right: one label every 10 cm. Optional dark
    digit-sized blobs left of the ruler mimic leaves reaching into the ruler zone.
    """
    import cv2

    w, h = 600, 900
    arr = np.full((h, w, 3), 255, dtype=np.uint8)
    base = h - 60
    for value in labels:
        y = int(base - value * px_per_cm)
        cv2.line(arr, (470, y), (490, y), (0, 0, 0), 1)
        cv2.putText(arr, str(value), (500, y + 7), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    if leaf_blobs:
        for y in (330, 352, 395, 470):
            arr[y - 18:y, 345:365] = (30, 60, 30)
    return _png(arr)


def potted_plant_image(plant_h: int = 300, droop: int = 40, pot_h: int = 90, scale_px_per_cm: float = 10.0) -> bytes:
    """
    Green plant standing in a black pot; one leaf hangs down over the pot by `droop` px.
    Height from the soil line (pot rim) is plant_h px; the lowest green pixel lies lower.
    """
    w, h = 400, 600
    arr = np.full((h, w, 3), 235, dtype=np.uint8)
    green = PLANT_GREEN[::-1]
    rim = h - 60 - pot_h
    arr[rim:h - 60, 120:220] = (20, 20, 20)                  # pot with soil
    arr[rim - plant_h:rim, 160:180] = green                    # stem and canopy
    arr[rim - plant_h:rim - plant_h + 80, 120:220] = green
    arr[rim - 30:rim + droop, 200:230] = green                 # leaf hanging over the rim
    return _png(arr)
