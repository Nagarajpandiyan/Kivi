import sys
import tempfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

import os

_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["KIVI_DB_PATH"] = _tmp_db.name

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
client.__enter__()  # trigger startup lifespan (applies migrations) once for the module


@pytest.fixture(autouse=True)
def reset_between_tests():
    client.post("/api/reset")
    yield


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_full_learning_and_apply_flow():
    client.post("/api/memory/learn", json={
        "user_id": "u1", "asr": "ask aditya to call me", "formatted": "Ask Aaditya to call me."
    })
    client.post("/api/memory/learn", json={
        "user_id": "u1", "asr": "meet aditya tomorrow", "formatted": "Meet Aaditya tomorrow."
    })

    memories = client.get("/api/memory", params={"user_id": "u1"}).json()
    assert len(memories) == 1
    assert memories[0]["status"] == "ACTIVE"

    result = client.post("/api/transcript/process", json={
        "user_id": "u1", "asr": "ask aditya about the meeting", "formatted": "Ask Aditya about the meeting."
    }).json()
    assert result["output"] == "Ask Aaditya about the meeting."
    assert result["decision"] == "APPLY"
    assert result["intervened"] is True


def test_deliberate_ignore_for_irrelevant_common_word():
    for asr, fmt in [
        ("ask aditya to review the sarvam kiwi service", "Ask Aditya to review the Sarvam Kivi service."),
        ("check the sarvam kiwi release notes", "Check the Sarvam Kivi release notes."),
    ]:
        client.post("/api/memory/learn", json={"user_id": "u2", "asr": asr, "formatted": fmt})

    result = client.post("/api/transcript/process", json={
        "user_id": "u2", "asr": "i ate a kiwi yesterday", "formatted": "I ate a kiwi yesterday."
    }).json()
    assert result["output"] == "I ate a kiwi yesterday."
    assert result["decision"] == "IGNORE"


def test_single_observation_stays_candidate_and_does_not_apply():
    client.post("/api/memory/learn", json={
        "user_id": "u3", "asr": "ask priya to join", "formatted": "Ask Priyaa to join."
    })
    memories = client.get("/api/memory", params={"user_id": "u3"}).json()
    assert memories[0]["status"] == "CANDIDATE"

    result = client.post("/api/transcript/process", json={
        "user_id": "u3", "asr": "call priya now", "formatted": "Call Priya now."
    }).json()
    assert result["decision"] == "IGNORE"
    assert result["output"] == "Call Priya now."


def test_deactivate_stops_future_application():
    client.post("/api/memory/learn", json={"user_id": "u4", "asr": "ask aditya", "formatted": "Ask Aaditya"})
    client.post("/api/memory/learn", json={"user_id": "u4", "asr": "call aditya", "formatted": "Call Aaditya"})
    mem_id = client.get("/api/memory", params={"user_id": "u4"}).json()[0]["id"]

    client.post(f"/api/memory/{mem_id}/deactivate")
    result = client.post("/api/transcript/process", json={
        "user_id": "u4", "asr": "email aditya", "formatted": "Email Aditya"
    }).json()
    assert result["decision"] == "IGNORE"
    assert "Aaditya" not in result["output"]


def test_reset_clears_state():
    client.post("/api/memory/learn", json={"user_id": "u5", "asr": "ask aditya", "formatted": "Ask Aaditya"})
    assert len(client.get("/api/memory", params={"user_id": "u5"}).json()) == 1
    client.post("/api/reset")
    assert client.get("/api/memory", params={"user_id": "u5"}).json() == []
