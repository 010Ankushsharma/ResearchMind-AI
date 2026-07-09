"""
tests/test_health.py

Smoke test for the FastAPI app — verifies the app imports cleanly and the
unauthenticated /api/health endpoint responds. Uses a plain (non-context-
manager) TestClient instantiation so the app's `lifespan` (which calls
`init_db()` against a real Postgres connection in dev mode) does NOT run —
keeping this test fast and independent of any live database/services.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

# Plain instantiation (no `with` block) intentionally skips the lifespan
# context manager, avoiding a real DB connection attempt during this test.
client = TestClient(app)


def test_health_check_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "app" in body


def test_openapi_schema_is_generated():
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"]


def test_protected_research_endpoint_requires_auth():
    # No Authorization header supplied -> should be rejected, not 200.
    response = client.get("/api/research")
    assert response.status_code in (401, 403)
