from fastapi.testclient import TestClient

from api.main import app


def test_root_serves_frontend_and_health_endpoint_works():
    client = TestClient(app)

    root = client.get("/")
    assert root.status_code == 200
    assert "DriveInOne" in root.text

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
