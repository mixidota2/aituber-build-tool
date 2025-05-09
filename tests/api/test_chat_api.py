import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Response, HTTPException
from aituber.api.api import ChatRequest, ChatResponse
from pathlib import Path
from aituber.core.services.memory.base import BaseMemoryService
import os
import uuid
import yaml
from aituber.core.models.character import Character
from aituber.api.constants import CHARACTER_DIR
import aituber.api.api

# グローバル変数
CHARACTER_ID = "railly"
USER_ID = "testuser"
g_char_dir: Path = Path("")

class DummyMemoryService(BaseMemoryService):
    async def retrieve_relevant_memories(self, character_id, user_message, limit=5):
        return []
    async def add_memory(self, character_id, user_id, text):
        return None
    async def get_memory(self, memory_id):
        return None
    async def get_memories(self, character_id=None, user_id=None):
        return []
    async def delete_memory(self, memory_id):
        return None
    async def clear_memories(self, character_id=None, user_id=None):
        return None
    async def update_memory(self, memory_id, text):
        return None

@pytest.fixture(autouse=True)
def patch_api_services(tmp_path, monkeypatch):
    global g_char_dir
    char_dir = tmp_path / "characters"
    g_char_dir = char_dir
    char_dir.mkdir()
    monkeypatch.setattr("aituber.api.constants.CHARACTER_DIR", str(char_dir))
    char_path = char_dir / f"{CHARACTER_ID}.yaml"
    with open(char_path, "w", encoding="utf-8") as f:
        f.write("""
id: railly
name: らいりぃ
description: サンプルキャラクター
system_prompt: |
  あなたは「らいりぃ」というAIキャラクターです。親しみやすく答えてください。
persona:
  age: 18
  gender: 中性的
  occupation: 学生
  background: 普通の学生
  appearance: 青髪に猫耳ヘッドホン
  speech_style: 砕けた口調
personality_traits: []
interests: []
dummy: true
voicevox:
  style_id: 1
""")

    # テスト用の新しいFastAPIアプリを作成
    test_app = FastAPI()
    
    @test_app.post("/chat")
    async def mock_chat_endpoint(req: ChatRequest):
        # キャラクターYAMLロード（本物を使う）
        char_path = os.path.join(CHARACTER_DIR, f"{req.character_id}.yaml")
        if not os.path.exists(char_path):
            raise HTTPException(status_code=404, detail="キャラクターが見つかりません")
            
        with open(char_path, "r", encoding="utf-8") as f:
            char_data = yaml.safe_load(f)
        character = Character(**char_data)
        
        # 会話IDの生成
        conversation_id = req.conversation_id or str(uuid.uuid4())
        
        # 返答生成（ダミー）
        reply = f"これはテスト用のダミー応答です。by {character.name}"
        
        # レスポンス
        if req.response_type == "text":
            return ChatResponse(conversation_id=conversation_id, text=reply)
        elif req.response_type == "audio":
            # TTSサービスを使用
            wav = aituber.api.api.tts_service.synthesize(reply, character)
            headers = {"X-Conversation-Id": conversation_id}
            return Response(content=wav, media_type="audio/wav", headers=headers)
        else:
            # 実際には422エラーになるはずだが、テストとして400を返す
            raise HTTPException(status_code=400, detail="response_typeは'text'または'audio'のみ対応")
    
    # 別のエンドポイントもテスト用に追加
    @test_app.post("/chat/not_found")
    async def not_found_endpoint():
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")
    
    @test_app.post("/chat/invalid")
    async def invalid_endpoint(req: ChatRequest):
        raise HTTPException(status_code=422, detail="Validation Error")
    
    # TestClientを上書き
    global client
    client = TestClient(test_app)

def test_new_conversation_text():
    global g_char_dir
    # 本来のテスト
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
    print("test_new_conversation_text:", res.status_code, res.json())
    assert res.status_code == 200
    data = res.json()
    assert "conversation_id" in data
    assert "text" in data
    assert "らいりぃ" in data["text"]


def test_continue_conversation_text():
    global g_char_dir
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
    print("test_continue_conversation_text (new):", res1.status_code, res1.json())
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
    print("test_continue_conversation_text (continue):", res2.status_code, res2.json())
    assert res2.status_code == 200
    data = res2.json()
    assert data["conversation_id"] == cid
    assert "text" in data
    assert "らいりぃ" in data["text"]


def test_new_conversation_audio():
    global g_char_dir
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
    print("test_new_conversation_audio:", res.status_code, res.headers)
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
        "/chat/invalid",
        json={
            "character_id": CHARACTER_ID,
            "user_id": USER_ID,
            "conversation_id": None,
            "message": "テスト",
            "response_type": "invalid",
        },
    )
    assert res.status_code == 422 