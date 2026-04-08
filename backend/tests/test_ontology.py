import pytest

pytestmark = pytest.mark.asyncio

class TestTraits:
    async def test_create_trait(self, client, auth_headers):
        resp = await client.post("/api/traits", json={
            "traitName": "Plant height",
            "traitClass": "morphological",
            "entity": "Stem",
            "attribute": "Height",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["traitName"] == "Plant height"

    async def test_list_traits(self, client, auth_headers):
        await client.post("/api/traits", json={"traitName": "T1"}, headers=auth_headers)
        resp = await client.get("/api/traits", headers=auth_headers)
        assert resp.status_code == 200

class TestMethods:
    async def test_create_method(self, client, auth_headers):
        resp = await client.post("/api/methods", json={
            "methodName": "Ruler measurement",
            "methodClass": "measurement",
            "description": "Manual measurement",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["methodName"] == "Ruler measurement"

    async def test_list_methods(self, client, auth_headers):
        await client.post("/api/methods", json={"methodName": "M1"}, headers=auth_headers)
        resp = await client.get("/api/methods", headers=auth_headers)
        assert resp.status_code == 200

class TestScales:
    async def test_create_scale(self, client, auth_headers):
        resp = await client.post("/api/scales", json={
            "scaleName": "Centimeters",
            "dataType": "numerical",
            "units": "cm",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["scaleName"] == "Centimeters"

    async def test_list_scales(self, client, auth_headers):
        await client.post("/api/scales", json={"scaleName": "S1"}, headers=auth_headers)
        resp = await client.get("/api/scales", headers=auth_headers)
        assert resp.status_code == 200

class TestVariables:
    async def test_create_variable(self, client, auth_headers):
        resp = await client.post("/api/variables", json={
            "name": "Plant height (ruler, cm)",
            "traitId": "t1",
            "methodId": "m1",
            "scaleId": "sc1",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Plant height (ruler, cm)"

    async def test_list_variables(self, client, auth_headers):
        await client.post("/api/variables", json={"name": "V1", "traitId": "t1", "methodId": "m1", "scaleId": "s1"}, headers=auth_headers)
        resp = await client.get("/api/variables", headers=auth_headers)
        assert resp.status_code == 200
