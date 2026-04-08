import pytest

pytestmark = pytest.mark.asyncio

class TestPrograms:
    async def test_create_program(self, client, auth_headers):
        resp = await client.post("/api/programs", json={
            "name": "Wheat Breeding",
            "abbreviation": "WB",
            "objective": "High yield",
            "crop": "Triticum aestivum",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Wheat Breeding"
        assert "id" in data

    async def test_list_programs(self, client, auth_headers):
        await client.post("/api/programs", json={"name": "P1"}, headers=auth_headers)
        await client.post("/api/programs", json={"name": "P2"}, headers=auth_headers)
        resp = await client.get("/api/programs", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    async def test_create_program_unauthenticated(self, client):
        resp = await client.post("/api/programs", json={"name": "X"})
        assert resp.status_code == 403
