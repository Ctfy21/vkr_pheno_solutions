import pytest

pytestmark = pytest.mark.asyncio

class TestTrials:
    async def test_create_trial(self, client, auth_headers):
        resp = await client.post("/api/trials", json={
            "name": "Spring 2025",
            "programId": "pr1",
            "startDate": "2025-01-10",
            "endDate": "2025-06-30",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Spring 2025"

    async def test_list_trials(self, client, auth_headers):
        await client.post("/api/trials", json={"name": "T1", "programId": "pr1"}, headers=auth_headers)
        resp = await client.get("/api/trials", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
