import cv2
import numpy as np
import pytest

from app.analyze import detect_ruler, measure_plant_height, plantcv_rgb_analysis
from tests.helpers import plant_image, potted_plant_image, ruler_scene


SCALE = 10.0  # px per cm


class TestAlgorithms:
    def test_height_and_area_on_synthetic_plant(self):
        m = measure_plant_height(plant_image(height_px=200, width_px=60), scale_px_per_cm=SCALE)
        assert m["height_cm"] == pytest.approx(20.0, abs=0.2)
        assert m["leaf_area_cm2"] == pytest.approx(120.0, rel=0.03)
        assert m["scale_source"] == "manual"

    def test_rgb_pipeline_extracts_both_traits(self):
        m = plantcv_rgb_analysis(plant_image(height_px=300, width_px=80), scale_px_per_cm=SCALE)
        assert m["height_cm"] == pytest.approx(30.0, abs=0.2)
        assert m["leaf_area_cm2"] == pytest.approx(240.0, rel=0.03)
        assert m["bbox_width_cm"] == pytest.approx(8.0, abs=0.2)
        assert 0 < m["compactness"] <= 1

    def test_jpeg_artifacts_do_not_break_measurement(self):
        m = measure_plant_height(plant_image(height_px=150, width_px=50, fmt="JPEG"), scale_px_per_cm=SCALE)
        assert m["height_cm"] == pytest.approx(15.0, abs=0.3)

    def test_empty_scene(self):
        m = plantcv_rgb_analysis(plant_image(height_px=0, width_px=0), scale_px_per_cm=SCALE)
        assert m["height_cm"] == 0.0 and m["leaf_area_cm2"] == 0.0

    def test_undecodable_bytes(self):
        assert "error" in measure_plant_height(b"garbage", scale_px_per_cm=SCALE)

    def test_ruler_scale_ignores_blobs_outside_the_ruler(self):
        img = cv2.imdecode(np.frombuffer(ruler_scene(px_per_cm=11.0), np.uint8), cv2.IMREAD_COLOR)
        ruler = detect_ruler(img)
        assert ruler["px_per_cm"] == pytest.approx(11.0, rel=0.02)
        assert ruler["labels"] == 7
        assert ruler["left_x"] < 470 + 5

    def test_ruler_scale_survives_a_missing_label(self):
        img = cv2.imdecode(np.frombuffer(ruler_scene(labels=[10, 20, 40, 50, 60], leaf_blobs=False), np.uint8),
                           cv2.IMREAD_COLOR)
        assert detect_ruler(img)["px_per_cm"] == pytest.approx(10.0, rel=0.02)

    def test_height_is_measured_from_the_pot_rim(self):
        m = plantcv_rgb_analysis(potted_plant_image(plant_h=300, droop=40), scale_px_per_cm=SCALE)
        assert m["base_source"] == "pot_rim"
        assert m["height_cm"] == pytest.approx(30.0, abs=0.3)
        assert m["lowest_green_y"] > m["bottom_y"]

    def test_without_a_pot_height_uses_the_lowest_green_pixel(self):
        m = plantcv_rgb_analysis(plant_image(height_px=300, width_px=80), scale_px_per_cm=SCALE)
        assert m["base_source"] == "lowest_green"
        assert m["bottom_y"] == m["lowest_green_y"]


async def seed_experiment(client, headers, db):
    study = (await client.post("/api/studies", json={
        "name": "Соя, засуха",
        "studyType": "phenotyping",
        "plants": [
            {"name": "P1", "treatment": "Контроль"}, {"name": "P2", "treatment": "Контроль"},
            {"name": "P3", "treatment": "Засуха"}, {"name": "P4", "treatment": "Засуха"},
        ],
    }, headers=headers)).json()
    await db.phenotyping_solutions.insert_one({
        "_id": "sol-rgb",
        "name": "PlantCV RGB Workflow",
        "config": {"scale_px_per_cm": SCALE, "method": "plantcv_rgb_analysis_v1"},
        "outputVariables": [
            {"coTermId": "CO_321:0000020", "name": "Plant height", "unit": "см"},
            {"coTermId": "CO_321:0000080", "name": "Leaf area", "unit": "см²"},
        ],
    })
    # Two capture dates; drought plants are shorter and grow slower
    sizes = {
        ("P1", "2026-03-01"): (150, 50), ("P2", "2026-03-01"): (160, 50),
        ("P3", "2026-03-01"): (110, 40), ("P4", "2026-03-01"): (100, 40),
        ("P1", "2026-03-08"): (220, 60), ("P2", "2026-03-08"): (230, 60),
        ("P3", "2026-03-08"): (130, 45), ("P4", "2026-03-08"): (120, 45),
    }
    for i, ((plant, day), (h, w)) in enumerate(sizes.items()):
        resp = await client.post(
            "/api/images/upload-batch",
            files=[("files", (f"{plant}_{day}.png", plant_image(height_px=h, width_px=w, seed_color=i), "image/png"))],
            data={"studyId": study["id"], "folderName": "Съёмка", "capturedAt": f"{day}T09:00:00Z"},
            headers=headers,
        )
        assert resp.json()[0]["observationUnitId"], "file name must be matched to the plant"
    return study


class TestPipeline:
    async def test_run_analysis_and_trait_summary(self, client, auth_headers, db, brapi_db):
        study = await seed_experiment(client, auth_headers, db)
        resp = await client.post(f"/api/studies/{study['id']}/run-analysis",
                                 json={"solution_id": "sol-rgb", "folder_name": "Съёмка"}, headers=auth_headers)
        assert resp.status_code == 200, resp.text

        run = (await client.get(f"/api/studies/{study['id']}/analysis-runs", headers=auth_headers)).json()[0]
        assert len(run["results"]) == 8
        first = run["results"][0]
        assert first["capturedAt"] == "2026-03-01T09:00:00Z"
        by_co = {m["coTermId"]: m for m in first["measurements"] if m["coTermId"]}
        assert by_co["CO_321:0000020"]["unit"] == "см"
        assert by_co["CO_321:0000080"]["unit"] == "см²"
        assert first["annotatedImageId"]
        assert (await brapi_db.studies.find_one({"_id": study["id"]}))["status"] == "completed"

        summary = (await client.get(f"/api/studies/{study['id']}/trait-summary", headers=auth_headers)).json()
        assert summary["images"] == 8 and summary["plants"] == 4
        assert summary["dates"] == ["2026-03-01", "2026-03-08"]
        height = next(t for t in summary["traits"] if t["key"] == "height")
        area = next(t for t in summary["traits"] if t["key"] == "leaf_area")
        assert height["overall"]["n"] == 8
        assert [d["date"] for d in height["dynamics"]] == ["2026-03-01", "2026-03-08"]
        assert height["dynamics"][1]["mean"] > height["dynamics"][0]["mean"]
        groups = {g["treatment"]: g for g in height["byTreatment"]}
        assert groups["Контроль"]["mean"] > groups["Засуха"]["mean"]
        assert height["comparisons"][0]["reference"] == "Контроль"
        by_date = height["comparisonsByDate"]
        assert [c["date"] for c in by_date] == ["2026-03-01", "2026-03-08"]
        assert all(c["group"] == "Засуха" and c["meanDiff"] < 0 for c in by_date)
        growth = {g["plant"]: g for g in height["growth"]}
        assert growth["P1"]["days"] == 7
        assert growth["P1"]["agr"] == pytest.approx((22.0 - 15.0) / 7, abs=0.05)
        assert growth["P1"]["agr"] > growth["P3"]["agr"]
        assert area["overall"]["n"] == 8
        assert summary["correlation"]["r"] > 0.9

    async def test_tampered_image_is_not_analysed(self, client, auth_headers, db, storage):
        study = await seed_experiment(client, auth_headers, db)
        img = await db.images.find_one({"fileName": "P1_2026-03-01.png"})
        storage.files[img["gridfsId"]]["data"] = plant_image(height_px=10)
        await client.post(f"/api/studies/{study['id']}/run-analysis",
                          json={"solution_id": "sol-rgb", "folder_name": "Съёмка"}, headers=auth_headers)
        run = (await client.get(f"/api/studies/{study['id']}/analysis-runs", headers=auth_headers)).json()[0]
        bad = next(r for r in run["results"] if r["imageId"] == img["_id"])
        assert bad["metric"] == "error" and "integrity" in bad["value"]

    async def test_run_analysis_unknown_folder(self, client, auth_headers, db):
        study = await seed_experiment(client, auth_headers, db)
        resp = await client.post(f"/api/studies/{study['id']}/run-analysis",
                                 json={"solution_id": "sol-rgb", "folder_name": "нет такой"}, headers=auth_headers)
        assert resp.status_code == 400
