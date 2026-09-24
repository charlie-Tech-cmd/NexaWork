from app.api.dependencies import get_db
from app.main import app


def test_health_endpoint(client, caplog):
    caplog.set_level("INFO", logger="nexawork.request")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"message": "NexaWork API is running"}
    assert "GET /health -> 200" in caplog.text

def test_readiness_endpoint(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"message": "NexaWork API is ready"}

def test_readiness_endpoint_returns_503_when_database_fails(client):
    class FailingSession:
        def execute(self, query):
            raise RuntimeError("database unavailable")

    def failing_db():
        yield FailingSession()

    app.dependency_overrides[get_db] = failing_db

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "NexaWork API is not ready"}
