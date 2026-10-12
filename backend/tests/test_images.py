import hashlib
from urllib.parse import parse_qs, urlparse

import pytest

from app.config import SIGNED_URL_SECRET
from app.image_meta import (content_disposition, detect_image_type, parse_datetime, resolve_capture_time,
                            safe_filename, sign_link, verify_link)
from app.routers import images as images_router
from tests.helpers import plant_image



async def upload(client, headers, files, **form):
    data = {k: v for k, v in form.items() if v is not None}
    return await client.post(
        "/api/images/upload-batch",
        files=[("files", (name, content, mime)) for name, content, mime in files],
        data=data,
        headers=headers,
    )


async def create_study(brapi_db, study_id="st1", plants=(), chamber_id=None):
    await brapi_db.studies.insert_one({"_id": study_id, "name": "Соя 2026", "status": "draft",
                                       "climateChamberId": chamber_id})
    for i, (name, treatment) in enumerate(plants):
        await brapi_db.observation_units.insert_one({"_id": f"{study_id}-ou{i}", "name": name, "studyId": study_id,
                                                    "treatment": treatment})


class TestHelpers:
    def test_detect_image_type_by_signature(self):
        assert detect_image_type(plant_image(fmt="PNG")) == "image/png"
        assert detect_image_type(plant_image(fmt="JPEG")) == "image/jpeg"
        assert detect_image_type(b"%PDF-1.7 not an image") is None
        assert detect_image_type(b"") is None

    def test_safe_filename_strips_paths_and_control_chars(self):
        assert safe_filename("../../etc/passwd") == "passwd"
        assert safe_filename("C:\\photos\\P1\x00.jpg") == "P1.jpg"
        assert safe_filename("") == "image"

    def test_content_disposition_handles_cyrillic(self):
        header = content_disposition("attachment", "Соя опыт 1.xlsx")
        assert header.startswith("attachment; filename=")
        assert "filename*=UTF-8''" in header
        header.encode("latin-1")  # must be a valid HTTP header

    def test_parse_datetime_formats(self):
        assert parse_datetime("2026-03-01T10:00:00Z").isoformat() == "2026-03-01T10:00:00+00:00"
        assert parse_datetime("2026-03-01T13:00:00+03:00").isoformat() == "2026-03-01T10:00:00+00:00"
        assert parse_datetime("1772359200000").isoformat() == "2026-03-01T10:00:00+00:00"  # browser lastModified, ms
        assert parse_datetime("not a date") is None

    def test_capture_time_priority_and_sanity(self):
        now = parse_datetime("2026-04-01T00:00:00Z")
        exif = parse_datetime("2026-03-01T10:00:00Z")
        client = parse_datetime("2026-03-02T10:00:00Z")
        assert resolve_capture_time(exif, client, now) == (exif, "exif")
        assert resolve_capture_time(None, client, now) == (client, "client")
        assert resolve_capture_time(None, None, now) == (now, "server")
        # camera clock in the future or reset to 1970 is ignored
        assert resolve_capture_time(parse_datetime("2099-01-01T00:00:00Z"), client, now)[1] == "client"
        assert resolve_capture_time(parse_datetime("1980-01-01T00:00:00Z"), None, now)[1] == "server"

    def test_signed_links(self):
        exp, sig = sign_link("secret", "original", "img1", 60, now=1000)
        assert verify_link("secret", "original", "img1", exp, sig, now=1000)
        assert not verify_link("secret", "original", "img2", exp, sig, now=1000)      # other file
        assert not verify_link("secret", "annotated", "img1", exp, sig, now=1000)     # other kind
        assert not verify_link("other", "original", "img1", exp, sig, now=1000)       # other key
        assert not verify_link("secret", "original", "img1", exp, sig, now=exp + 1)   # expired
        assert not verify_link("secret", "original", "img1", "abc", sig, now=1000)

    def test_match_plant_prefers_longest_name(self):
        plants = [("P1", "a"), ("P10", "b")]
        assert images_router.match_plant("P10_day3.jpg", plants) == ("P10", "b")
        assert images_router.match_plant("p1-side.jpg", plants) == ("P1", "a")
        assert images_router.match_plant("unknown.jpg", plants) == ("", "")


class TestUpload:
    async def test_upload_binds_exif_time_and_checksum(self, client, auth_headers, db, brapi_db):
        await create_study(brapi_db, plants=[("P1", "Контроль")])
        content = plant_image(exif_time="2026:03:01 13:15:00", offset="+03:00")
        resp = await upload(client, auth_headers, [("P1_day1.jpg", content, "application/octet-stream")],
                            studyId="st1", folderName="День 1")
        assert resp.status_code == 200
        img = resp.json()[0]
        assert img["mimeType"] == "image/jpeg"  # taken from the file signature, not the header
        assert img["sha256"] == hashlib.sha256(content).hexdigest()
        assert img["capturedAt"] == "2026-03-01T10:15:00Z"
        assert img["capturedAtSource"] == "exif"
        assert img["cameraMake"] == "PhenoCam"
        assert img["observationUnitId"] == "st1-ou0"
        assert img["uploadedBy"] == "admin@test.ru"
        assert "url" in img and "sig=" in img["url"]
        assert await db.image_audit.count_documents({"action": "upload"}) == 1

    async def test_client_time_used_without_exif(self, client, auth_headers, brapi_db):
        await create_study(brapi_db)
        resp = await upload(client, auth_headers, [("a.png", plant_image(), "image/png")],
                            studyId="st1", folderName="f", capturedAt="2026-03-05T08:00:00Z")
        assert resp.json()[0]["capturedAtSource"] == "client"
        assert resp.json()[0]["capturedAt"] == "2026-03-05T08:00:00Z"

    async def test_server_time_as_last_resort(self, client, auth_headers, brapi_db):
        await create_study(brapi_db)
        resp = await upload(client, auth_headers, [("a.png", plant_image(), "image/png")], studyId="st1")
        assert resp.json()[0]["capturedAtSource"] == "server"

    async def test_batch_capture_times_align_with_files(self, client, auth_headers, brapi_db):
        await create_study(brapi_db)
        resp = await client.post(
            "/api/images/upload-batch",
            files=[("files", ("a.png", plant_image(seed_color=1), "image/png")),
                   ("files", ("b.png", plant_image(seed_color=2), "image/png"))],
            data={"studyId": "st1", "capturedAt": ["2026-03-01T10:00:00Z", "2026-03-08T10:00:00Z"]},
            headers=auth_headers,
        )
        assert [i["capturedAt"][:10] for i in resp.json()] == ["2026-03-01", "2026-03-08"]

    async def test_non_image_rejected(self, client, auth_headers, db):
        resp = await client.post("/api/images/upload", files={"file": ("x.jpg", b"#!/bin/sh\nrm -rf /", "image/jpeg")},
                                 headers=auth_headers)
        assert resp.status_code == 415
        batch = await upload(client, auth_headers, [("x.jpg", b"not an image", "image/jpeg"),
                                                    ("ok.png", plant_image(), "image/png")], studyId="st1")
        results = batch.json()
        assert results[0]["status"] == "rejected" and "Неподдерживаемый формат" in results[0]["error"]
        assert results[1]["status"] == "pending"
        assert await db.images.count_documents({}) == 1

    async def test_size_limit(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(images_router, "IMAGE_MAX_BYTES", 100)
        resp = await client.post("/api/images/upload", files={"file": ("big.png", plant_image(), "image/png")},
                                 headers=auth_headers)
        assert resp.status_code == 413

    async def test_duplicate_in_study_is_not_stored_twice(self, client, auth_headers, db, storage, brapi_db):
        await create_study(brapi_db)
        content = plant_image()
        first = await upload(client, auth_headers, [("a.png", content, "image/png")], studyId="st1")
        second = await upload(client, auth_headers, [("copy.png", content, "image/png")], studyId="st1")
        assert second.json()[0]["duplicate"] is True
        assert second.json()[0]["uploadedName"] == "copy.png" and second.json()[0]["fileName"] == "a.png"
        assert second.json()[0]["id"] == first.json()[0]["id"]
        assert await db.images.count_documents({}) == 1
        assert len(storage.files) == 1

    async def test_upload_requires_auth(self, client):
        resp = await client.post("/api/images/upload", files={"file": ("a.png", plant_image(), "image/png")})
        assert resp.status_code == 403


class TestDownload:
    async def _one(self, client, headers, brapi_db):
        await create_study(brapi_db)
        content = plant_image()
        resp = await upload(client, headers, [("a.png", content, "image/png")], studyId="st1")
        return resp.json()[0], content

    async def test_download_requires_token_or_signature(self, client, auth_headers, brapi_db):
        img, content = await self._one(client, auth_headers, brapi_db)
        assert (await client.get(f"/api/images/file/{img['id']}")).status_code == 401

        with_token = await client.get(f"/api/images/file/{img['id']}", headers=auth_headers)
        assert with_token.status_code == 200
        assert with_token.content == content
        assert with_token.headers["x-content-sha256"] == img["sha256"]
        assert with_token.headers["x-content-type-options"] == "nosniff"

        signed = await client.get(img["url"])
        assert signed.status_code == 200 and signed.content == content

    async def test_forged_or_expired_signature_rejected(self, client, auth_headers, brapi_db, db):
        img, _ = await self._one(client, auth_headers, brapi_db)
        q = parse_qs(urlparse(img["url"]).query)
        forged = await client.get(f"/api/images/file/{img['id']}?exp={q['exp'][0]}&sig={'0' * 64}")
        assert forged.status_code == 401
        exp, sig = sign_link(SIGNED_URL_SECRET, "original", img["id"], ttl_seconds=-10)
        expired = await client.get(f"/api/images/file/{img['id']}?exp={exp}&sig={sig}")
        assert expired.status_code == 401
        assert await db.image_audit.count_documents({"action": "download_denied"}) == 2

    async def test_signed_urls_endpoint(self, client, auth_headers, brapi_db):
        img, content = await self._one(client, auth_headers, brapi_db)
        resp = await client.post("/api/images/signed-urls", json={"imageIds": [img["id"]], "annotatedIds": []},
                                 headers=auth_headers)
        url = resp.json()["images"][img["id"]]
        assert (await client.get(url)).content == content
        assert (await client.post("/api/images/signed-urls", json={"imageIds": [img["id"]]})).status_code == 403

    async def test_tampered_file_is_detected(self, client, auth_headers, brapi_db, storage, db):
        img, _ = await self._one(client, auth_headers, brapi_db)
        storage.files[img["gridfsId"]]["data"] = plant_image(height_px=50)  # silent substitution in storage

        resp = await client.get(f"/api/images/file/{img['id']}", headers=auth_headers)
        assert resp.status_code == 409
        verify = await client.get(f"/api/images/{img['id']}/verify", headers=auth_headers)
        assert verify.json()["ok"] is False
        report = (await client.get("/api/images/integrity/st1", headers=auth_headers)).json()
        assert report["failed"] == [img["id"]] and report["ok"] == 0
        assert await db.image_audit.count_documents({"action": "integrity_failed"}) == 1

    async def test_integrity_report_ok(self, client, auth_headers, brapi_db):
        await self._one(client, auth_headers, brapi_db)
        report = (await client.get("/api/images/integrity/st1", headers=auth_headers)).json()
        assert report["checked"] == 1 and report["ok"] == 1 and report["failed"] == []


class TestTimeAxis:
    async def test_timeline_groups_by_capture_date(self, client, auth_headers, brapi_db):
        await create_study(brapi_db, plants=[("P1", ""), ("P2", "")])
        files = [
            ("P1_a.jpg", plant_image(exif_time="2026:03:01 09:00:00", seed_color=1), "image/jpeg"),
            ("P2_a.jpg", plant_image(exif_time="2026:03:01 09:05:00", seed_color=2), "image/jpeg"),
            ("P1_b.jpg", plant_image(exif_time="2026:03:08 09:00:00", seed_color=3), "image/jpeg"),
        ]
        await upload(client, auth_headers, files, studyId="st1", folderName="Съёмка")
        tl = (await client.get("/api/images/timeline/st1", headers=auth_headers)).json()
        assert [(d["date"], d["count"], d["plants"]) for d in tl["days"]] == [("2026-03-01", 2, 2), ("2026-03-08", 1, 1)]
        assert tl["days"][0]["firstAt"] == "2026-03-01T09:00:00Z"

    async def test_image_linked_to_climate_readings(self, client, auth_headers, brapi_db):
        chamber = (await client.post("/api/climate-chambers", json={
            "name": "КУС-01",
            "sensors": [{"id": "t", "name": "Температура", "type": "temperature", "unit": "°C"},
                        {"id": "rh", "name": "Влажность", "type": "humidity", "unit": "%"}],
        }, headers=auth_headers)).json()
        for sensor, ts, value in [("t", "2026-03-01T08:40:00Z", 21.0), ("t", "2026-03-01T09:02:00Z", 23.5),
                                  ("rh", "2026-03-01T09:10:00Z", 61.0), ("t", "2026-03-01T12:00:00Z", 30.0)]:
            r = await client.post("/api/sensor-readings", json={"chamberId": chamber["id"], "sensorId": sensor,
                                                                 "value": value, "timestamp": ts}, headers=auth_headers)
            assert r.status_code == 200
        await create_study(brapi_db, chamber_id=chamber["id"])
        img = (await upload(client, auth_headers, [("P1.jpg", plant_image(exif_time="2026:03:01 09:00:00"), "image/jpeg")],
                            studyId="st1")).json()[0]
        env = (await client.get(f"/api/images/{img['id']}/environment", headers=auth_headers)).json()
        by_sensor = {r["sensorId"]: r for r in env["readings"]}
        assert by_sensor["t"]["value"] == 23.5 and by_sensor["t"]["deltaSeconds"] == 120
        assert by_sensor["rh"]["value"] == 61.0 and by_sensor["rh"]["unit"] == "%"

    async def test_sensor_reading_rejects_bad_timestamp(self, client, auth_headers):
        r = await client.post("/api/sensor-readings", json={"chamberId": "c", "sensorId": "s", "value": 1,
                                                            "timestamp": "вчера"}, headers=auth_headers)
        assert r.status_code == 422


class TestDelete:
    async def test_observer_cannot_delete(self, client, auth_headers, observer_headers, researcher_headers, brapi_db, db, storage):
        await create_study(brapi_db)
        img = (await upload(client, auth_headers, [("a.png", plant_image(), "image/png")], studyId="st1")).json()[0]
        assert (await client.delete(f"/api/images/{img['id']}", headers=observer_headers)).status_code == 403
        assert (await client.delete(f"/api/images/{img['id']}", headers=researcher_headers)).status_code == 200
        assert await db.images.count_documents({}) == 0
        assert storage.files == {}
        assert await db.image_audit.count_documents({"action": "delete"}) == 1
