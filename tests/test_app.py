import pytest
import json
from unittest.mock import AsyncMock, patch


@pytest.fixture
def access_code(monkeypatch):
    monkeypatch.setenv("NEUROSIM_ACCESS_CODE", "testpass")
    monkeypatch.setenv("STANFORD_API_KEY", "fake-key")


@pytest.fixture
def client(access_code):
    from neurosim.app import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_cookie(client):
    """Get a valid auth cookie by authenticating."""
    response = client.post("/api/auth", json={"passphrase": "testpass"})
    assert response.status_code == 200
    return response.cookies


def test_auth_correct_passphrase(client):
    response = client.post("/api/auth", json={"passphrase": "testpass"})
    assert response.status_code == 200
    assert "neurosim_token" in response.cookies


def test_auth_wrong_passphrase(client):
    response = client.post("/api/auth", json={"passphrase": "wrong"})
    assert response.status_code == 401


def test_api_requires_auth(client):
    response = client.post("/api/session/start", json={"role": "clinician"})
    assert response.status_code == 401


def test_start_clinician_session(client, auth_cookie):
    response = client.post(
        "/api/session/start",
        json={"role": "clinician"},
        cookies=auth_cookie,
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["disorder_info"] is None


def test_start_patient_session(client, auth_cookie):
    response = client.post(
        "/api/session/start",
        json={"role": "patient"},
        cookies=auth_cookie,
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["disorder_info"] is not None
    assert "name" in data["disorder_info"]


def test_diagnose_incorrect(client, auth_cookie):
    start_resp = client.post(
        "/api/session/start",
        json={"role": "clinician"},
        cookies=auth_cookie,
    )
    session_id = start_resp.json()["session_id"]

    async def mock_llm_no(messages, system_prompt, model="claude-4-5-sonnet"):
        yield "NO"

    with patch("neurosim.app.stream_chat", side_effect=mock_llm_no):
        response = client.post(
            "/api/diagnose",
            json={"session_id": session_id, "diagnosis": "Definitely Not A Real Disorder XYZ"},
            cookies=auth_cookie,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["correct"] is False


def test_reveal_returns_disorder(client, auth_cookie):
    start_resp = client.post(
        "/api/session/start",
        json={"role": "clinician"},
        cookies=auth_cookie,
    )
    session_id = start_resp.json()["session_id"]

    response = client.post(
        "/api/reveal",
        json={"session_id": session_id},
        cookies=auth_cookie,
    )
    assert response.status_code == 200
    data = response.json()
    assert "disorder" in data
    assert "name" in data["disorder"]
    assert "feedback" in data


def test_reveal_deactivates_session(client, auth_cookie):
    start_resp = client.post(
        "/api/session/start",
        json={"role": "clinician"},
        cookies=auth_cookie,
    )
    session_id = start_resp.json()["session_id"]

    client.post("/api/reveal", json={"session_id": session_id}, cookies=auth_cookie)

    response = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "hello"},
        cookies=auth_cookie,
    )
    assert response.status_code == 400


def test_auth_check_with_valid_cookie(client, auth_cookie):
    response = client.get("/api/auth/check", cookies=auth_cookie)
    assert response.status_code == 200


def test_auth_check_without_cookie(client):
    response = client.get("/api/auth/check")
    assert response.status_code == 401


def test_chat_streams_tokens(client, auth_cookie):
    start_resp = client.post(
        "/api/session/start",
        json={"role": "clinician"},
        cookies=auth_cookie,
    )
    session_id = start_resp.json()["session_id"]

    async def mock_stream(messages, system_prompt, model="claude-4-5-sonnet"):
        for token in ["Hello", ", ", "how ", "can ", "I ", "help?"]:
            yield token

    with patch("neurosim.app.stream_chat", side_effect=mock_stream):
        response = client.post(
            "/api/chat",
            json={"session_id": session_id, "message": "What seems to be the problem?"},
            cookies=auth_cookie,
        )
        assert response.status_code == 200
        text = response.text
        assert '"token"' in text
        assert '"done": true' in text
