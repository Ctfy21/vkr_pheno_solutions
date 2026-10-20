"""
Plant height measurement using OpenCV — optimized version (MAE = 1.60 cm).
HSV green segmentation with auto-calibration from ruler marks.
Measures from plant base (top edge of the pot, or the lowest green pixel when
no pot is found) to top (highest green pixel).
"""
import cv2
import numpy as np

# Optimized parameters from AutoResearch (130 experiments, MAE=1.60cm)
DEFAULT_PARAMS = {
    "h_low": 29, "h_high": 86,
    "s_low": 17, "v_low": 34,
    "open_iter": 0, "close_iter": 4, "close_k": 9,
    "min_area_pct": 0.0003,
    "mask_right_cut": 0.7368,
}


FALLBACK_PX_PER_CM = 12.0
RULER_ROI_START = 0.55   # the ruler stands in the right part of the frame
RULER_COLUMN_PX = 40     # digit labels of one ruler share a column of this half-width
RULER_GAP_TOLERANCE = 0.15


def _ruler_digit_boxes(image: np.ndarray) -> list:
    """Bounding boxes (x, y, w, h) of digit-like blobs in the right part of the frame."""
    h_img, w_img = image.shape[:2]
    x0 = int(w_img * RULER_ROI_START)
    gray = cv2.cvtColor(image[:, x0:], cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 21, 10,
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        if 10 < h < 60 and 5 < w < 50 and area > 50:
            if 0.15 < w / h < 2.0 and area / (w * h) > 0.15:
                boxes.append((x + x0, y, w, h))
    return boxes


def _ruler_column(boxes: list) -> list:
    """
    Keep the blobs that stand in one vertical column: the ruler labels. Leaves and
    pot labels that happen to lie in the right part of the frame are dropped.
    """
    if not boxes:
        return []
    centers = [x + w / 2.0 for x, _, w, _ in boxes]
    best = max(range(len(boxes)), key=lambda i: sum(abs(c - centers[i]) <= RULER_COLUMN_PX for c in centers))
    column = [b for b, c in zip(boxes, centers) if abs(c - centers[best]) <= RULER_COLUMN_PX]
    # Re-centre on the column median so one stray blob does not pick the window
    mid = sorted(x + w / 2.0 for x, _, w, _ in column)[len(column) // 2]
    return [b for b, c in zip(boxes, centers) if abs(c - mid) <= RULER_COLUMN_PX]


def detect_ruler(image: np.ndarray) -> dict:
    """
    Find the ruler and its scale from the 10 cm labels.

    Returns px_per_cm (None when fewer than two labels are found), the number of
    labels used and left_x, the left edge of the ruler zone for masking it out.
    """
    column = _ruler_column(_ruler_digit_boxes(image))
    bottoms = sorted(y + h for _, y, _, h in column)
    labels = bottoms[:1]
    for b in bottoms[1:]:
        if b - labels[-1] > 15:  # two-digit labels split into separate blobs
            labels.append(b)
    out = {"px_per_cm": None, "labels": len(labels), "left_x": None}
    if column:
        digit_h = sorted(h for _, _, _, h in column)[len(column) // 2]
        # Tick marks stand left of the labels, about four label heights long
        out["left_x"] = max(int(image.shape[1] * RULER_ROI_START), min(x for x, _, _, _ in column) - 4 * digit_h)
    if len(labels) < 2:
        return out

    gaps = [labels[i + 1] - labels[i] for i in range(len(labels) - 1)]
    med = sorted(gaps)[len(gaps) // 2]
    steps = []
    for g in gaps:
        k = max(1, round(g / med))  # a missed label doubles the gap
        if abs(g / k - med) <= RULER_GAP_TOLERANCE * med and g / k > 10:
            steps.append(g / k)
    if not steps:
        steps = gaps
    out["px_per_cm"] = sum(steps) / len(steps) / 10.0
    return out


def _compute_scale(image: np.ndarray) -> float:
    """Auto-detect px/cm scale from ruler marks in right side of image."""
    return detect_ruler(image)["px_per_cm"] or FALLBACK_PX_PER_CM


def _get_green_mask(image: np.ndarray, p: dict) -> np.ndarray:
    """Create green vegetation mask with optimized HSV parameters."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(
        hsv,
        np.array([p["h_low"], p["s_low"], p["v_low"]]),
        np.array([p["h_high"], 255, 255]),
    )
    k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (p["close_k"], p["close_k"]))
    if p["open_iter"] > 0:
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k_open, iterations=p["open_iter"])
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k_close, iterations=p["close_iter"])

    # Exclude ruler area on the right
    h_img, w_img = mask.shape
    mask[:, int(w_img * p["mask_right_cut"]):] = 0
    return mask


def _prepare(img: np.ndarray, scale_px_per_cm: float):
    """
    Scale and green mask for one image. The ruler zone is masked out from where the
    ruler actually stands, so leaves reaching towards it are kept.
    """
    h_img, w_img = img.shape[:2]
    ruler = detect_ruler(img)
    if scale_px_per_cm > 0:
        px_per_cm, source = scale_px_per_cm, "manual"
    elif ruler["px_per_cm"]:
        px_per_cm, source = ruler["px_per_cm"], "auto_ruler"
    else:
        px_per_cm, source = FALLBACK_PX_PER_CM, "fallback"
    p = dict(DEFAULT_PARAMS)
    if ruler["px_per_cm"] and ruler["left_x"]:
        p["mask_right_cut"] = round(ruler["left_x"] / w_img, 4)
    return px_per_cm, source, p, _get_green_mask(img, p), ruler


POT_DARK_V = 100         # black pot and soil are darker than the wall, the table and lit leaves
POT_MIN_WIDTH_CM = 4.0
POT_JOIN_GAP_CM = 1.5    # pieces of the pot split by its label or by leaves are joined


def _find_pot_top(img: np.ndarray, mask: np.ndarray, bbox: tuple, px_per_cm: float) -> int:
    """
    Top edge of the dark pot under the plant (the soil line), or -1 when there is no pot.
    Plant height is measured from here, so leaves hanging over the pot rim do not add to it.
    """
    bx, by, bw, bh = bbox
    h_img, w_img = mask.shape
    y0 = by + bh // 2
    x_lo, x_hi = max(0, bx), min(w_img, bx + bw)
    if x_hi - x_lo < 2 or y0 >= h_img:
        return -1
    hsv = cv2.cvtColor(img[y0:, x_lo:x_hi], cv2.COLOR_BGR2HSV)
    dark = ((hsv[:, :, 2] < POT_DARK_V) & (mask[y0:, x_lo:x_hi] == 0)).astype(np.uint8) * 255
    k = max(3, int(px_per_cm * 0.5)) | 1
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    n, _, stats, _ = cv2.connectedComponentsWithStats(dark)
    pieces = [stats[i] for i in range(1, n) if stats[i][4] >= k * k * 4]
    min_w = POT_MIN_WIDTH_CM * px_per_cm
    bodies = [s for s in pieces if s[2] >= min_w and s[3] >= min_w / 2 and s[4] >= 0.3 * s[2] * s[3]]
    if not bodies:
        return -1
    body = max(bodies, key=lambda s: s[4])
    left, right, top, bottom = body[0], body[0] + body[2], body[1], body[1] + body[3]
    gap = POT_JOIN_GAP_CM * px_per_cm
    grown = True
    while grown:  # climb up through pot-wide pieces (rim, soil) that stand over the pot body
        grown = False
        for x, y, w, h, _ in pieces:
            overlap = min(right, x + w) - max(left, x)
            if y < top and overlap >= 0.6 * (right - left) and y + h >= top - gap:
                top, grown = y, True
    return int(y0 + top)


def _significant_contours(mask: np.ndarray, p: dict) -> list:
    h_img, w_img = mask.shape
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = h_img * w_img * p["min_area_pct"]
    return [c for c in contours if cv2.contourArea(c) > min_area]


def _plant_extent(img: np.ndarray, mask: np.ndarray, p: dict, px_per_cm: float) -> dict:
    """
    Top of the plant (highest green pixel) and its base: the soil line at the top of
    the pot when a pot is found under the plant, otherwise the lowest green pixel.
    """
    h_img = mask.shape[0]
    significant = _significant_contours(mask, p)
    if not significant:
        return {"significant": [], "bbox": None, "top_y": h_img, "base_y": h_img,
                "lowest_green_y": h_img, "base_source": "none"}
    bbox = cv2.boundingRect(np.vstack(significant))
    bx, by, bw, bh = bbox
    lowest = by + bh
    pot_top = _find_pot_top(img, mask, bbox, px_per_cm)
    if by < pot_top <= lowest + int(2 * px_per_cm):
        base, source = pot_top, "pot_rim"
    else:
        base, source = lowest, "lowest_green"
    return {"significant": significant, "bbox": bbox, "top_y": by, "base_y": base,
            "lowest_green_y": lowest, "base_source": source}


def measure_plant_height(image_bytes: bytes, scale_px_per_cm: float = 0.0) -> dict:
    """
    Measure plant height from image bytes.

    Args:
        image_bytes: raw JPEG/PNG bytes
        scale_px_per_cm: if > 0, use this fixed scale; if 0, auto-detect from ruler

    Returns:
        dict with height_cm, height_px, scale, bbox, method info
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return {"error": "Cannot decode image", "height_px": 0, "height_cm": 0.0}

    h_img, w_img = img.shape[:2]
    px_per_cm, scale_source, p, mask, ruler = _prepare(img, scale_px_per_cm)

    # Find top and base of plant
    ext = _plant_extent(img, mask, p, px_per_cm)
    top_y, bot_y = ext["top_y"], ext["base_y"]

    height_px = max(0, bot_y - top_y)
    height_cm = round(height_px / px_per_cm, 1) if px_per_cm > 0 else 0.0
    height_cm = max(0.0, min(height_cm, 100.0))  # cap at 100cm (ruler length)

    green_area = int(cv2.countNonZero(mask))
    leaf_area_cm2 = round(green_area / (px_per_cm ** 2), 2) if px_per_cm > 0 else 0.0

    return {
        "height_px": int(height_px),
        "height_cm": height_cm,
        "leaf_area_cm2": leaf_area_cm2,
        "top_y": int(top_y),
        "bottom_y": int(bot_y),
        "lowest_green_y": int(ext["lowest_green_y"]),
        "base_source": ext["base_source"],
        "image_height": int(h_img),
        "height_ratio": round(height_px / h_img, 4) if h_img > 0 else 0.0,
        "green_area_px": green_area,
        "scale_px_per_cm": round(px_per_cm, 2),
        "scale_source": scale_source,
        "ruler_labels": ruler["labels"],
        "params": p,
        "method": "hsv_optimized_autoResearch_v2",
    }



def plantcv_rgb_analysis(image_bytes: bytes, scale_px_per_cm: float = 0.0) -> dict:
    """
    Full PlantCV-style RGB analysis: height, leaf area, green index, compactness, bbox width.

    Args:
        image_bytes: raw JPEG/PNG bytes
        scale_px_per_cm: if > 0, use this fixed scale; if 0, auto-detect from ruler

    Returns:
        dict with height_cm, leaf_area_cm2, green_index, compactness, bbox_width_cm, etc.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return {"error": "Cannot decode image", "height_cm": 0.0, "leaf_area_cm2": 0.0,
                "green_index": 0.0, "compactness": 0.0, "bbox_width_cm": 0.0}

    h_img, w_img = img.shape[:2]
    px_per_cm, scale_source, p, mask, ruler = _prepare(img, scale_px_per_cm)

    ext = _plant_extent(img, mask, p, px_per_cm)
    significant = ext["significant"]

    if not significant:
        return {
            "height_px": 0, "height_cm": 0.0,
            "leaf_area_px": 0, "leaf_area_cm2": 0.0,
            "green_index": 0.0, "compactness": 0.0,
            "bbox_width_px": 0, "bbox_width_cm": 0.0,
            "top_y": h_img, "bottom_y": h_img,
            "image_height": int(h_img),
            "scale_px_per_cm": round(px_per_cm, 2),
            "scale_source": scale_source,
            "method": "plantcv_rgb_analysis_v1",
            "contours_count": 0,
        }

    bx, by, bw, bh = ext["bbox"]

    # --- Plant height: from the soil line (or lowest green pixel) to the top ---
    top_y = ext["top_y"]
    bot_y = ext["base_y"]
    height_px = max(0, bot_y - top_y)
    height_cm = round(height_px / px_per_cm, 1) if px_per_cm > 0 else 0.0
    height_cm = max(0.0, min(height_cm, 100.0))

    # --- Leaf area (green pixels) ---
    green_area_px = int(cv2.countNonZero(mask))
    leaf_area_cm2 = round(green_area_px / (px_per_cm ** 2), 2) if px_per_cm > 0 else 0.0

    # --- Green index (mean green channel in plant region) ---
    green_channel = img[:, :, 1]  # BGR -> G channel
    plant_green_values = green_channel[mask > 0]
    green_index = round(float(np.mean(plant_green_values)), 1) if len(plant_green_values) > 0 else 0.0

    # --- Compactness (4*pi*area / perimeter^2) ---
    total_area = sum(cv2.contourArea(c) for c in significant)
    total_perimeter = sum(cv2.arcLength(c, True) for c in significant)
    if total_perimeter > 0:
        compactness = round((4.0 * 3.14159 * total_area) / (total_perimeter ** 2), 4)
    else:
        compactness = 0.0

    # --- Bounding box width ---
    bbox_width_px = bw
    bbox_width_cm = round(bw / px_per_cm, 1) if px_per_cm > 0 else 0.0

    return {
        "height_px": int(height_px),
        "height_cm": height_cm,
        "leaf_area_px": green_area_px,
        "leaf_area_cm2": leaf_area_cm2,
        "green_index": green_index,
        "compactness": compactness,
        "bbox_width_px": int(bbox_width_px),
        "bbox_width_cm": bbox_width_cm,
        "top_y": int(top_y),
        "bottom_y": int(bot_y),
        "lowest_green_y": int(ext["lowest_green_y"]),
        "base_source": ext["base_source"],
        "bbox_x": int(bx),
        "bbox_y": int(by),
        "bbox_w": int(bw),
        "bbox_h": int(bh),
        "image_height": int(h_img),
        "height_ratio": round(height_px / h_img, 4) if h_img > 0 else 0.0,
        "green_area_px": green_area_px,
        "scale_px_per_cm": round(px_per_cm, 2),
        "scale_source": scale_source,
        "ruler_labels": ruler["labels"],
        "method": "plantcv_rgb_analysis_v1",
        "contours_count": len(significant),
        "params": p,
    }


def create_annotated_image(image_bytes: bytes, measurement: dict) -> bytes:
    """
    Create an annotated image showing plant measurement.
    For PlantCV RGB analysis: draws contour outline + height + metrics.
    For simple height: draws top/bottom lines + height arrow.

    Returns: JPEG bytes of annotated image.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return image_bytes

    h_img, w_img = img.shape[:2]
    top_y = measurement.get("top_y", 0)
    bot_y = measurement.get("bottom_y", h_img)
    height_cm = measurement.get("height_cm", 0)
    is_plantcv = measurement.get("method", "").startswith("plantcv_rgb")

    # Create overlay for semi-transparent drawing
    overlay = img.copy()

    # Plant region - right boundary (exclude ruler area)
    p = measurement.get("params", DEFAULT_PARAMS)
    right_bound = int(w_img * p.get("mask_right_cut", 0.7))

    # For PlantCV: draw green contour around detected plant
    if is_plantcv:
        mask = _get_green_mask(img, p)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = h_img * w_img * p.get("min_area_pct", 0.0003)
        significant = [c for c in contours if cv2.contourArea(c) > min_area]
        # Draw green contour outline
        cv2.drawContours(overlay, significant, -1, (0, 255, 0), 2)
        # Draw bounding box in cyan
        bx = measurement.get("bbox_x", 0)
        by = measurement.get("bbox_y", 0)
        bw = measurement.get("bbox_w", 0)
        bh = measurement.get("bbox_h", 0)
        if bw > 0 and bh > 0:
            cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), (255, 255, 0), 1)

    # Draw horizontal lines at top and bottom
    cv2.line(overlay, (0, top_y), (right_bound, top_y), (0, 0, 255), 2)
    cv2.line(overlay, (0, bot_y), (right_bound, bot_y), (0, 0, 255), 2)

    # Draw vertical height line with arrows - green
    mid_x = right_bound // 2
    cv2.arrowedLine(overlay, (mid_x, bot_y - 5), (mid_x, top_y + 5), (0, 255, 0), 3, tipLength=0.03)
    cv2.arrowedLine(overlay, (mid_x, top_y + 5), (mid_x, bot_y - 5), (0, 255, 0), 3, tipLength=0.03)

    # Height label
    font = cv2.FONT_HERSHEY_SIMPLEX
    label = f"{height_cm} cm"
    font_scale = 1.2
    thickness = 3
    (tw, th), baseline = cv2.getTextSize(label, font, font_scale, thickness)

    label_y = (top_y + bot_y) // 2
    label_x = mid_x + 15

    cv2.rectangle(overlay,
                  (label_x - 5, label_y - th - 10),
                  (label_x + tw + 10, label_y + 10),
                  (0, 0, 0), -1)
    cv2.putText(overlay, label, (label_x, label_y), font, font_scale, (0, 255, 0), thickness)

    # TOP / BASE labels
    cv2.putText(overlay, "TOP", (10, top_y - 10), font, 0.7, (0, 0, 255), 2)
    cv2.putText(overlay, "BASE", (10, bot_y + 25), font, 0.7, (0, 0, 255), 2)

    # For PlantCV: add extra metric labels in top-left corner
    if is_plantcv:
        info_lines = []
        if "leaf_area_cm2" in measurement:
            info_lines.append(f"Area: {measurement['leaf_area_cm2']} cm2")
        if "green_index" in measurement:
            info_lines.append(f"Green idx: {measurement['green_index']}")
        if "compactness" in measurement:
            info_lines.append(f"Compact: {measurement['compactness']}")
        if "bbox_width_cm" in measurement:
            info_lines.append(f"Width: {measurement['bbox_width_cm']} cm")
        for i, line in enumerate(info_lines):
            y_pos = 30 + i * 25
            (ltw, lth), _ = cv2.getTextSize(line, font, 0.6, 2)
            cv2.rectangle(overlay, (5, y_pos - lth - 3), (10 + ltw + 5, y_pos + 5), (0, 0, 0), -1)
            cv2.putText(overlay, line, (10, y_pos), font, 0.6, (0, 255, 200), 2)

    # Blend overlay
    result = cv2.addWeighted(overlay, 0.85, img, 0.15, 0)

    _, buf = cv2.imencode(".jpg", result, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buf.tobytes()
