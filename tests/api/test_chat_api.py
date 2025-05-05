import pytest
from fastapi.testclient import TestClient
from aituber.api.api import app

client = TestClient(app)

# サンプルキャラクターID
CHARACTER_ID = "railly"
USER_ID = "testuser"

@pytest.fixture(autouse=True)
def patch_character_dir(tmp_path, monkeypatch):
    char_dir = tmp_path / "characters"
    char_dir.mkdir()
    monkeypatch.setattr("aituber.api.constants.CHARACTER_DIR", str(char_dir))
    # テスト用キャラクターYAMLを作成
    char_path = char_dir / f"{CHARACTER_ID}.yaml"
    with open(char_path, "w", encoding="utf-8") as f:
        f.write("""
id: railly
name: らいりぃ
description: サンプルキャラクター
dummy: true
voicevox:
  style_id: 1
""")


def test_new_conversation_text():
    res = client.post(
        "/chat",
        json={
            "character_id": CHARACTER_ID,
            "user_id": USER_ID,
            "conversation_id": None,
            "message": "こんにちは",
            "response_type": "text",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "conversation_id" in data
    assert "text" in data
    assert "らいりぃ" in data["text"]


def test_continue_conversation_text():
    # まず新規会話
    res1 = client.post(
        "/chat",
        json={
            "character_id": CHARACTER_ID,
            "user_id": USER_ID,
            "conversation_id": None,
            "message": "はじめまして",
            "response_type": "text",
        },
    )
    cid = res1.json()["conversation_id"]
    # 継続会話
    res2 = client.post(
        "/chat",
        json={
            "character_id": CHARACTER_ID,
            "user_id": USER_ID,
            "conversation_id": cid,
            "message": "元気ですか？",
            "response_type": "text",
        },
    )
    assert res2.status_code == 200
    data = res2.json()
    assert data["conversation_id"] == cid
    assert "text" in data
    assert "らいりぃ" in data["text"]


def test_new_conversation_audio():
    res = client.post(
        "/chat",
        json={
            "character_id": CHARACTER_ID,
            "user_id": USER_ID,
            "conversation_id": None,
            "message": "音声で返して",
            "response_type": "audio",
        },
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("audio/wav")
    assert res.headers.get("x-conversation-id")
    assert isinstance(res.content, bytes)
    assert len(res.content) > 100  # wavバイナリの簡易判定


def test_not_found_character():
    res = client.post(
        "/chat",
        json={
            "character_id": "notfound",
            "user_id": USER_ID,
            "conversation_id": None,
            "message": "テスト",
            "response_type": "text",
        },
    )
    assert res.status_code == 404


def test_invalid_response_type():
    res = client.post(
        "/chat",
        json={
            "character_id": CHARACTER_ID,
            "user_id": USER_ID,
            "conversation_id": None,
            "message": "テスト",
            "response_type": "invalid",
        },
    )
    assert res.status_code == 422 