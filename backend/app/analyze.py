"""
Plant height measurement using OpenCV — optimized version (MAE = 1.60 cm).
HSV green segmentation with auto-calibration from ruler marks.
Measures from plant base (lowest green pixel) to top (highest green pixel).
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


def _compute_scale(image: np.ndarray) -> float:
    """Auto-detect px/cm scale from ruler marks in right side of image."""
    h_img, w_img = image.shape[:2]
    roi = image[:, int(w_img * 0.55):]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 21, 10,
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    digits = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        if 10 < h < 60 and 5 < w < 50 and area > 50:
            if 0.15 < w / h < 2.0 and area / (w * h) > 0.15:
                digits.append(y + h)
    digits.sort()

    if digits:
        filtered = [digits[0]]
        for d in digits[1:]:
            if d - filtered[-1] > 15:
                filtered.append(d)
        digits = filtered

    if len(digits) < 2:
        return 12.0  # fallback

    gaps = [digits[i + 1] - digits[i] for i in range(len(digits) - 1)]
    med = sorted(gaps)[len(gaps) // 2]
    good = [g for g in gaps if 0.4 * med < g < 2.5 * med and g > 10]
    if not good:
        good = gaps

    return sum(good) / len(good) / 10.0


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


def _find_plant_top(mask: np.ndarray, p: dict) -> int:
    """Find topmost green pixel (highest point of plant)."""
    h_img, w_img = mask.shape
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = h_img * w_img * p["min_area_pct"]
    significant = [c for c in contours if cv2.contourArea(c) > min_area]
    if not significant:
        return h_img
    all_pts = np.vstack(significant)
    _, top_y, _, _ = cv2.boundingRect(all_pts)
    return top_y


def _find_plant_bottom(mask: np.ndarray, p: dict) -> int:
    """Find bottommost green pixel (base of plant)."""
    h_img, w_img = mask.shape
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = h_img * w_img * p["min_area_pct"]
    significant = [c for c in contours if cv2.contourArea(c) > min_area]
    if not significant:
        return h_img
    all_pts = np.vstack(significant)
    x, y, w, h = cv2.boundingRect(all_pts)
    return y + h


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
    p = DEFAULT_PARAMS

    # Auto-detect scale from ruler if not provided
    if scale_px_per_cm <= 0:
        px_per_cm = _compute_scale(img)
    else:
        px_per_cm = scale_px_per_cm

    # Create green mask
    mask = _get_green_mask(img, p)

    # Find top and bottom of plant
    top_y = _find_plant_top(mask, p)
    bot_y = _find_plant_bottom(mask, p)

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
        "image_height": int(h_img),
        "height_ratio": round(height_px / h_img, 4) if h_img > 0 else 0.0,
        "green_area_px": green_area,
        "scale_px_per_cm": round(px_per_cm, 2),
        "scale_source": "auto_ruler" if scale_px_per_cm <= 0 else "manual",
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
    p = DEFAULT_PARAMS

    # Auto-detect scale from ruler if not provided
    if scale_px_per_cm <= 0:
        px_per_cm = _compute_scale(img)
    else:
        px_per_cm = scale_px_per_cm

    # Create green mask
    mask = _get_green_mask(img, p)

    # Find significant contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = h_img * w_img * p["min_area_pct"]
    significant = [c for c in contours if cv2.contourArea(c) > min_area]

    if not significant:
        return {
            "height_px": 0, "height_cm": 0.0,
            "leaf_area_px": 0, "leaf_area_cm2": 0.0,
            "green_index": 0.0, "compactness": 0.0,
            "bbox_width_px": 0, "bbox_width_cm": 0.0,
            "top_y": h_img, "bottom_y": h_img,
            "image_height": int(h_img),
            "scale_px_per_cm": round(px_per_cm, 2),
            "scale_source": "auto_ruler" if scale_px_per_cm <= 0 else "manual",
            "method": "plantcv_rgb_analysis_v1",
            "contours_count": 0,
        }

    all_pts = np.vstack(significant)
    bx, by, bw, bh = cv2.boundingRect(all_pts)

    # --- Plant height ---
    top_y = by
    bot_y = by + bh
    height_px = bh
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
        "bbox_x": int(bx),
        "bbox_y": int(by),
        "bbox_w": int(bw),
        "bbox_h": int(bh),
        "image_height": int(h_img),
        "height_ratio": round(height_px / h_img, 4) if h_img > 0 else 0.0,
        "green_area_px": green_area_px,
        "scale_px_per_cm": round(px_per_cm, 2),
        "scale_source": "auto_ruler" if scale_px_per_cm <= 0 else "manual",
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
    right_bound = int(w_img * 0.7)

    # For PlantCV: draw green contour around detected plant
    if is_plantcv:
        p = measurement.get("params", DEFAULT_PARAMS)
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
