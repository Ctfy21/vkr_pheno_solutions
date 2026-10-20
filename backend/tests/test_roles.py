import pytest

from tests.helpers import plant_image
from tests.test_images import create_study, upload

pytestmark = pytest.mark.asyncio


class TestObserverIsReadOnly:
    async def test_observer_cannot_create_or_delete(self, client, observer_headers, brapi_db):
        await create_study(brapi_db)
        await brapi_db.programs.insert_one({"_id": "p1", "name": "Соя"})
        writes = [
            lambda: client.post("/api/programs", json={"name": "Пшеница"}, headers=observer_headers),
            lambda: client.delete("/api/programs/p1", headers=observer_headers),
            lambda: client.post("/api/studies", json={"name": "Опыт"}, headers=observer_headers),
            lambda: client.delete("/api/studies/st1", headers=observer_headers),
            lambda: client.post("/api/studies/st1/run-analysis", json={}, headers=observer_headers),
            lambda: client.post("/api/variables", json={"name": "Высота", "traitId": "t", "methodId": "m",
                                                        "scaleId": "s"}, headers=observer_headers),
            lambda: upload(client, observer_headers, [("a.png", plant_image(), "image/png")], studyId="st1"),
        ]
        for send in writes:
            resp = await send()
            assert resp.status_code == 403, (resp.request.method, resp.request.url.path, resp.text)
        assert await brapi_db.programs.count_documents({}) == 1
        assert await brapi_db.studies.count_documents({}) == 1

    async def test_observer_still_reads(self, client, auth_headers, observer_headers, brapi_db):
        await create_study(brapi_db)
        img = (await upload(client, auth_headers, [("a.png", plant_image(), "image/png")], studyId="st1")).json()[0]
        assert (await client.get("/api/studies", headers=observer_headers)).status_code == 200
        assert (await client.get("/api/programs", headers=observer_headers)).status_code == 200
        signed = await client.post("/api/images/signed-urls", json={"imageIds": [img["id"]]}, headers=observer_headers)
        assert signed.status_code == 200 and img["id"] in signed.json()["images"]

    async def test_researcher_writes(self, client, researcher_headers, brapi_db):
        resp = await client.post("/api/programs", json={"name": "Пшеница"}, headers=researcher_headers)
        assert resp.status_code == 200
        assert await brapi_db.programs.count_documents({}) == 1

    async def test_missing_token_is_still_rejected(self, client):
        assert (await client.post("/api/programs", json={"name": "Пшеница"})).status_code == 403


class TestBrapiSyncIsAdminOnly:
    async def test_only_admin_manages_brapi_servers(self, client, auth_headers, researcher_headers, db):
        server = {"name": "Внешний сервер", "url": "https://brapi.example.org/"}
        assert (await client.post("/api/admin/brapi-servers", json=server)).status_code == 403
        assert (await client.post("/api/admin/brapi-servers", json=server, headers=researcher_headers)).status_code == 403
        assert (await client.get("/api/admin/brapi-servers", headers=researcher_headers)).status_code == 403
        assert await db.brapi_servers.count_documents({}) == 0

        resp = await client.post("/api/admin/brapi-servers", json=server, headers=auth_headers)
        assert resp.status_code == 200 and resp.json()["url"] == "https://brapi.example.org"
        assert len((await client.get("/api/admin/brapi-servers", headers=auth_headers)).json()) == 1
