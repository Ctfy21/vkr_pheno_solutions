"""
Analysis of the two phenotypic traits extracted from plant images:
plant height (CO_321:0000020, cm) and projected leaf area (CO_321:0000080, cm²).

Pure functions without database access: descriptive statistics, comparison of
treatment groups (Welch's t-test), dynamics over capture dates, per-plant
growth rates and the height/area correlation.
"""
import math
from collections import defaultdict
from datetime import date
from typing import Dict, Iterable, List, Optional

PRIMARY_TRAITS = [
    {
        "key": "height",
        "coTermId": "CO_321:0000020",
        "metric": "height_cm",
        "name": "Высота растения",
        "unit": "см",
    },
    {
        "key": "leaf_area",
        "coTermId": "CO_321:0000080",
        "metric": "leaf_area_cm2",
        "name": "Площадь проекции листовой поверхности",
        "unit": "см²",
    },
]

NO_TREATMENT = "без обработки"
_ALPHA = 0.05


# ─── Distributions ───────────────────────────────────────────────

def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Numerical Recipes, 6.4)."""
    fpmin = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > fpmin else fpmin)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > fpmin else fpmin)
        c = 1.0 + aa / c
        c = c if abs(c) > fpmin else fpmin
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > fpmin else fpmin)
        c = 1.0 + aa / c
        c = c if abs(c) > fpmin else fpmin
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_bt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(ln_bt) * _betacf(a, b, x) / a
    return 1.0 - math.exp(ln_bt) * _betacf(b, a, 1.0 - x) / b


def t_two_sided_p(t: float, df: float) -> float:
    if df <= 0 or math.isnan(t):
        return float("nan")
    if math.isinf(t):
        return 0.0
    return betainc(df / 2.0, 0.5, df / (df + t * t))


def t_critical(df: float, alpha: float = _ALPHA) -> float:
    """Two-sided critical value of Student's t, found by bisection."""
    lo, hi = 0.0, 1000.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if t_two_sided_p(mid, df) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


# ─── Statistics ──────────────────────────────────────────────────

def _r(value: Optional[float], digits: int = 3) -> Optional[float]:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return None
    return round(value, digits)


def _p(value: float) -> float:
    """p-values keep three significant digits so very small values do not round to zero."""
    return float(f"{value:.3g}")


def describe(values: Iterable[float]) -> dict:
    vals = sorted(float(v) for v in values)
    n = len(vals)
    if n == 0:
        return {"n": 0, "mean": None, "sd": None, "sem": None, "min": None, "max": None,
                "median": None, "cv": None, "ci95Low": None, "ci95High": None}
    mean = sum(vals) / n
    mid = n // 2
    median = vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2.0
    out = {"n": n, "mean": _r(mean), "min": _r(vals[0]), "max": _r(vals[-1]), "median": _r(median),
           "sd": None, "sem": None, "cv": None, "ci95Low": None, "ci95High": None}
    if n >= 2:
        sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / (n - 1))
        sem = sd / math.sqrt(n)
        half = t_critical(n - 1) * sem
        out.update({
            "sd": _r(sd), "sem": _r(sem),
            "cv": _r(sd / mean * 100.0, 2) if mean else None,
            "ci95Low": _r(mean - half), "ci95High": _r(mean + half),
        })
    return out


def welch_test(a: List[float], b: List[float]) -> Optional[dict]:
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return None
    m1, m2 = sum(a) / n1, sum(b) / n2
    v1 = sum((x - m1) ** 2 for x in a) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in b) / (n2 - 1)
    se2 = v1 / n1 + v2 / n2
    if se2 == 0:
        if m1 == m2:
            return {"meanDiff": 0.0, "t": 0.0, "df": float(n1 + n2 - 2), "pValue": 1.0, "significant": False}
        return {"meanDiff": _r(m1 - m2), "t": None, "df": float(n1 + n2 - 2), "pValue": 0.0, "significant": True}
    t = (m1 - m2) / math.sqrt(se2)
    df = se2 ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))
    p = t_two_sided_p(t, df)
    return {"meanDiff": _r(m1 - m2), "t": _r(t), "df": _r(df, 1), "pValue": _p(p), "significant": p < _ALPHA}


def pearson(xs: List[float], ys: List[float]) -> Optional[dict]:
    n = len(xs)
    if n < 3 or n != len(ys):
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sxx * syy)
    r = max(-1.0, min(1.0, r))
    if abs(r) == 1.0:
        p = 0.0
    else:
        p = t_two_sided_p(r * math.sqrt((n - 2) / (1 - r * r)), n - 2)
    return {"n": n, "r": _r(r, 4), "pValue": _p(p), "significant": p < _ALPHA}


# ─── Records from analysis runs ──────────────────────────────────

def _trait_value(trait: dict, result: dict) -> Optional[float]:
    metrics = result.get("metrics") or {}
    if isinstance(metrics.get(trait["metric"]), (int, float)):
        return float(metrics[trait["metric"]])
    if trait["key"] == "leaf_area":
        # Older runs stored only the green pixel count and the scale
        px, scale = metrics.get("green_area_px"), metrics.get("scale_px_per_cm")
        if isinstance(px, (int, float)) and isinstance(scale, (int, float)) and scale > 0:
            return round(px / scale ** 2, 2)
    for m in result.get("measurements") or []:
        if m.get("coTermId") == trait["coTermId"] and m.get("unit") in (trait["unit"], "cm", "cm2", "см", "см²"):
            try:
                return float(m.get("value"))
            except (TypeError, ValueError):
                return None
    return None


def collect_records(runs: List[dict], images: Dict[str, dict], plants: Dict[str, dict]) -> List[dict]:
    """
    Flatten analysis runs into trait records. When one image was analysed several
    times only the most recent run is kept.

    images: image id -> image document (capturedAt, observationUnitId)
    plants: observation unit id -> plant document (name, treatment)
    """
    latest: Dict[tuple, dict] = {}
    for run in sorted(runs, key=lambda r: r.get("createdAt", "")):
        if run.get("status", "completed") != "completed":
            continue
        for res in run.get("results") or []:
            image = images.get(res.get("imageId", ""), {})
            plant = plants.get(image.get("observationUnitId", ""), {})
            captured = image.get("capturedAt") or ""
            for trait in PRIMARY_TRAITS:
                value = _trait_value(trait, res)
                if value is None:
                    continue
                latest[(res.get("imageId", ""), trait["key"])] = {
                    "trait": trait["key"],
                    "value": value,
                    "imageId": res.get("imageId", ""),
                    "fileName": res.get("fileName", ""),
                    "plant": plant.get("name") or res.get("plantName") or "",
                    "plantId": image.get("observationUnitId", ""),
                    "treatment": plant.get("treatment") or NO_TREATMENT,
                    "capturedAt": captured,
                    "date": captured[:10] or (run.get("createdAt", "") or "")[:10],
                    "runId": run.get("_id") or run.get("id", ""),
                    "studyId": run.get("studyId", ""),
                }
    return list(latest.values())


def _reference_group(groups: List[str]) -> str:
    for g in groups:
        low = g.lower()
        if "контрол" in low or "control" in low:
            return g
    return sorted(groups)[0]


def _days_between(d1: str, d2: str) -> int:
    return (date.fromisoformat(d2) - date.fromisoformat(d1)).days


def _growth(records: List[dict]) -> List[dict]:
    per_plant: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    meta: Dict[str, dict] = {}
    for rec in records:
        key = rec["plantId"] or rec["plant"]
        if not key or not rec["date"]:
            continue
        per_plant[key][rec["date"]].append(rec["value"])
        meta[key] = rec
    out = []
    for key, by_date in per_plant.items():
        dates = sorted(by_date)
        if len(dates) < 2:
            continue
        first = sum(by_date[dates[0]]) / len(by_date[dates[0]])
        last = sum(by_date[dates[-1]]) / len(by_date[dates[-1]])
        days = _days_between(dates[0], dates[-1])
        if days <= 0:
            continue
        rgr = (math.log(last) - math.log(first)) / days if first > 0 and last > 0 else None
        out.append({
            "plant": meta[key]["plant"], "treatment": meta[key]["treatment"],
            "firstDate": dates[0], "lastDate": dates[-1], "days": days,
            "firstValue": _r(first), "lastValue": _r(last),
            "agr": _r((last - first) / days, 4), "rgr": _r(rgr, 4),
        })
    return sorted(out, key=lambda g: g["plant"])


def summarize(records: List[dict]) -> dict:
    by_trait: Dict[str, List[dict]] = defaultdict(list)
    for rec in records:
        by_trait[rec["trait"]].append(rec)

    traits_out = []
    for trait in PRIMARY_TRAITS:
        recs = by_trait.get(trait["key"], [])
        groups: Dict[str, List[float]] = defaultdict(list)
        dates: Dict[str, List[float]] = defaultdict(list)
        group_dates: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        for rec in recs:
            groups[rec["treatment"]].append(rec["value"])
            if rec["date"]:
                dates[rec["date"]].append(rec["value"])
                group_dates[rec["treatment"]][rec["date"]].append(rec["value"])

        comparisons = []
        comparisons_by_date = []
        if len(groups) >= 2:
            ref = _reference_group(list(groups))
            for g in sorted(groups):
                if g == ref:
                    continue
                test = welch_test(groups[g], groups[ref])
                if test:
                    comparisons.append({"group": g, "reference": ref, **test})
            # Same comparison within each capture date: plants of the same age
            for day in sorted(dates):
                for g in sorted(groups):
                    if g == ref:
                        continue
                    test = welch_test(group_dates.get(g, {}).get(day, []), group_dates.get(ref, {}).get(day, []))
                    if test:
                        comparisons_by_date.append({"date": day, "group": g, "reference": ref, **test})

        traits_out.append({
            "key": trait["key"], "name": trait["name"], "unit": trait["unit"], "coTermId": trait["coTermId"],
            "overall": describe(r["value"] for r in recs),
            "byTreatment": [{"treatment": g, **describe(v)} for g, v in sorted(groups.items())],
            "comparisons": comparisons,
            "comparisonsByDate": comparisons_by_date,
            "dynamics": [{"date": d, **describe(v)} for d, v in sorted(dates.items())],
            "dynamicsByTreatment": [
                {"treatment": g, "points": [{"date": d, **describe(v)} for d, v in sorted(by_date.items())]}
                for g, by_date in sorted(group_dates.items())
            ],
            "growth": _growth(recs),
        })

    # Height vs area measured on the same image
    height = {r["imageId"]: r["value"] for r in by_trait.get("height", [])}
    area = {r["imageId"]: r["value"] for r in by_trait.get("leaf_area", [])}
    common = sorted(set(height) & set(area))
    correlation = pearson([height[i] for i in common], [area[i] for i in common])

    return {
        "traits": traits_out,
        "correlation": correlation,
        "records": len(records),
        "images": len({r["imageId"] for r in records}),
        "plants": len({r["plantId"] or r["plant"] for r in records if r["plantId"] or r["plant"]}),
        "dates": sorted({r["date"] for r in records if r["date"]}),
    }
