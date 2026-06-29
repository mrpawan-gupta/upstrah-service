from fastapi.testclient import TestClient

from upstrah.asgi import get_application


def test_liveness_ok() -> None:
    client = TestClient(get_application())
    response = client.get("/api/health/live")
    assert response.status_code == 200
