import pytest

from app.trait_analysis import (collect_records, describe, pearson, summarize, t_critical, t_two_sided_p,
                                welch_test)

# Reference values computed with scipy.stats 1.x


def test_describe_matches_reference():
    d = describe([12.1, 13.4, 11.8, 12.9, 13.1, 12.4])
    assert d["n"] == 6
    assert d["mean"] == pytest.approx(12.617, abs=1e-3)
    assert d["sd"] == pytest.approx(0.6178, abs=1e-3)
    assert d["sem"] == pytest.approx(0.2522, abs=1e-3)
    assert d["ci95Low"] == pytest.approx(11.968, abs=1e-3)
    assert d["ci95High"] == pytest.approx(13.265, abs=1e-3)
    assert d["median"] == pytest.approx(12.65)


def test_describe_small_samples():
    assert describe([])["n"] == 0
    one = describe([5.0])
    assert one["mean"] == 5.0 and one["sd"] is None


def test_student_t_distribution():
    assert t_critical(10) == pytest.approx(2.228139, abs=1e-5)
    assert t_critical(3) == pytest.approx(3.182446, abs=1e-5)
    assert t_two_sided_p(2.228139, 10) == pytest.approx(0.05, abs=1e-5)


def test_welch_matches_reference():
    res = welch_test([12.1, 13.4, 11.8, 12.9, 13.1, 12.4], [14.2, 15.1, 13.8, 14.9, 15.4])
    assert res["t"] == pytest.approx(-5.3096, abs=1e-3)
    assert res["df"] == pytest.approx(8.4, abs=0.05)
    assert res["pValue"] == pytest.approx(0.000616, abs=5e-5)
    assert res["significant"] is True
    assert welch_test([1.0], [2.0, 3.0]) is None


def test_pearson():
    res = pearson([1, 2, 3, 4, 5, 6], [2.1, 3.9, 6.2, 7.8, 10.1, 12.2])
    assert res["r"] == pytest.approx(0.9991, abs=1e-4)
    assert res["significant"] is True
    assert pearson([1, 2], [1, 2]) is None
    assert pearson([1, 1, 1], [1, 2, 3]) is None


def _run(created, results):
    return {"_id": created, "createdAt": created, "studyId": "s", "status": "completed", "results": results}


def test_collect_records_keeps_latest_run_and_derives_area():
    images = {"i1": {"capturedAt": "2026-03-01T09:00:00Z", "observationUnitId": "ou1"}}
    plants = {"ou1": {"name": "P1", "treatment": "Контроль"}}
    old = _run("2026-03-01 10:00", [{"imageId": "i1", "metrics": {"height_cm": 10.0, "leaf_area_cm2": 50.0}}])
    new = _run("2026-03-02 10:00", [{"imageId": "i1", "metrics": {"height_cm": 11.0, "green_area_px": 6000,
                                                                  "scale_px_per_cm": 10.0}}])
    recs = {r["trait"]: r for r in collect_records([new, old], images, plants)}
    assert recs["height"]["value"] == 11.0
    assert recs["leaf_area"]["value"] == 60.0  # 6000 px / (10 px/cm)²
    assert recs["height"]["plant"] == "P1" and recs["height"]["treatment"] == "Контроль"
    assert recs["height"]["date"] == "2026-03-01"


def test_summary_without_data():
    s = summarize([])
    assert s["records"] == 0 and s["correlation"] is None
    assert [t["key"] for t in s["traits"]] == ["height", "leaf_area"]
