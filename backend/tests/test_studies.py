import pytest

pytestmark = pytest.mark.asyncio

class TestStudies:
    async def test_create_study(self, client, auth_headers):
        resp = await client.post("/api/studies", json={
            "name": "Drought resistance 2025",
            "trialId": "tr1",
            "studyType": "Phenotyping",
            "plantCount": 120,
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Drought resistance 2025"
        assert data["plantCount"] == 120

    async def test_list_studies(self, client, auth_headers):
        await client.post("/api/studies", json={"name": "S1", "trialId": "tr1"}, headers=auth_headers)
        resp = await client.get("/api/studies", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
