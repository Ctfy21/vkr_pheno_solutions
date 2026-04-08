import pytest

pytestmark = pytest.mark.asyncio

class TestObservationUnits:
    async def test_create_observation_unit(self, client, auth_headers):
        resp = await client.post("/api/observationunits", json={
            "name": "NSK-67 / R1-P01",
            "studyId": "st1",
            "germplasmId": "g1",
            "position": "Row 1, Pos 1",
            "treatment": "Control",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "NSK-67 / R1-P01"

    async def test_list_observation_units(self, client, auth_headers):
        await client.post("/api/observationunits", json={
            "name": "OU1", "studyId": "st1", "germplasmId": "g1"
        }, headers=auth_headers)
        resp = await client.get("/api/observationunits", headers=auth_headers)
        assert resp.status_code == 200

class TestObservations:
    async def test_create_observation(self, client, auth_headers):
        resp = await client.post("/api/observations", json={
            "observationUnitId": "ou1",
            "variableId": "ov1",
            "variableName": "Plant height",
            "value": "42.5",
            "collector": "Test User",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["value"] == "42.5"

    async def test_list_observations(self, client, auth_headers):
        await client.post("/api/observations", json={
            "observationUnitId": "ou1", "variableId": "ov1", "value": "10"
        }, headers=auth_headers)
        resp = await client.get("/api/observations", headers=auth_headers)
        assert resp.status_code == 200

class TestDashboard:
    async def test_dashboard_stats(self, client, auth_headers):
        resp = await client.get("/api/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "programs" in data
        assert "experiments" in data

class TestClimateChambers:
    async def test_create_climate_chamber(self, client, auth_headers):
        resp = await client.post("/api/climate-chambers", json={
            "name": "KUS-01",
            "sensors": [{"name": "T1", "type": "temperature", "unit": "°C"}],
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "KUS-01"

    async def test_list_climate_chambers(self, client, auth_headers):
        resp = await client.get("/api/climate-chambers", headers=auth_headers)
        assert resp.status_code == 200

class TestSensorReadings:
    async def test_post_sensor_reading(self, client, auth_headers):
        resp = await client.post("/api/sensor-readings", json={
            "chamberId": "cc1",
            "sensorId": "s1",
            "value": 23.5,
            "timestamp": "2025-01-15T10:00:00Z",
        }, headers=auth_headers)
        assert resp.status_code == 200
