from fastapi.testclient import TestClient

from upstrah.api import create_fastapi_app


def test_health_ok() -> None:
    client = TestClient(create_fastapi_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
