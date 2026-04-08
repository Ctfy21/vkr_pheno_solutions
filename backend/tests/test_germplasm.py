import pytest

pytestmark = pytest.mark.asyncio

class TestGermplasm:
    async def test_create_germplasm(self, client, auth_headers):
        resp = await client.post("/api/germplasm", json={
            "germplasmName": "Novosibirskaya 67",
            "genus": "Triticum",
            "species": "aestivum",
            "accessionNumber": "NSK-67",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["germplasmName"] == "Novosibirskaya 67"

    async def test_list_germplasm(self, client, auth_headers):
        await client.post("/api/germplasm", json={"germplasmName": "G1"}, headers=auth_headers)
        resp = await client.get("/api/germplasm", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
