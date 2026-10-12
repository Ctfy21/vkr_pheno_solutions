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
