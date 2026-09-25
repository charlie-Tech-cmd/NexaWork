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


def test_cors_allows_configured_origin(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_security_headers_are_present(client):
    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

def test_rate_limit_settings_defaults():
    from app.core.config import Settings

    test_settings = Settings(
        _env_file=None,
        jwt_secret_key="test-secret-nexawork-@l2e-testing",
    )

    assert test_settings.rate_limit_max_attempts == 5
    assert test_settings.rate_limit_window_seconds == 60

def test_unexpected_exception_is_logged(client, caplog):
    caplog.set_level("ERROR", logger="nexawork.request")

    @app.get("/test-monitoring-error")
    async def monitoring_error():
        raise RuntimeError("test failure")

    from fastapi.testclient import TestClient

    test_client = TestClient(
        app,
        raise_server_exceptions=False,
    )

    response = test_client.get("/test-monitoring-error")

    assert response.status_code == 500
    assert "GET /test-monitoring-error -> 500" in caplog.text
    assert "RuntimeError: test failure" in caplog.text        
