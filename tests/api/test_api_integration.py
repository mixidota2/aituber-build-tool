import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import os
import yaml
from pathlib import Path

from aituber.api.api import app
from aituber.core.models.character import Character


@pytest.fixture
def test_character_dir():
    """テスト用のキャラクターディレクトリを作成"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        char_dir = Path(tmp_dir) / "characters"
        char_dir.mkdir()
        
        # テスト用キャラクターファイルを作成
        char_data = {
            "id": "test_char",
            "name": "テストキャラ",
            "description": "テスト用キャラクター",
            "system_prompt": "あなたはテスト用のAIです。",
            "persona": {
                "age": 20,
                "gender": "中性的",
                "occupation": "学生",
                "background": "テスト環境",
                "appearance": "シンプル",
                "speech_style": "丁寧語"
            },
            "personality_traits": ["親切", "聡明"],
            "interests": ["プログラミング", "テスト"],
            "voicevox": {
                "style_id": 1
            }
        }
        
        char_file = char_dir / "test_char.yaml"
        with open(char_file, "w", encoding="utf-8") as f:
            yaml.dump(char_data, f, allow_unicode=True)
        
        yield str(char_dir)


@pytest.fixture
def mock_app_services():
    """アプリケーションサービスをモック"""
    mock_app = Mock()
    mock_conversation_service = Mock()
    mock_conversation = Mock()
    mock_conversation.conversation_id = "test-conv-123"
    
    # 非同期メソッドのモック
    mock_conversation_service.get_or_create_conversation = Mock(return_value=mock_conversation)
    mock_conversation_service.process_message = AsyncMock(return_value="テスト応答")
    mock_conversation_service.process_message_stream = AsyncMock()
    
    async def mock_stream():
        chunks = ["テスト", "応答", "です"]
        for chunk in chunks:
            yield chunk
    
    mock_conversation_service.process_message_stream.return_value = mock_stream()
    
    mock_app.conversation_service = mock_conversation_service
    
    return mock_app


@pytest.fixture
def mock_tts_service():
    """TTSサービスをモック"""
    mock_tts = Mock()
    # ダミーのWAVデータ（最小限のWAVヘッダー）
    wav_data = b"RIFF\x24\x00\x00\x00WAVE" + b"\x00" * 32
    mock_tts.synthesize = Mock(return_value=wav_data)
    return mock_tts


@pytest.fixture
def client(test_character_dir, mock_app_services, mock_tts_service):
    """テスト用クライアント"""
    with patch("aituber.api.constants.CHARACTER_DIR", test_character_dir), \
         patch("aituber.api.api.get_app", return_value=mock_app_services), \
         patch("aituber.api.api.tts_service", mock_tts_service):
        
        # グローバル変数の初期化
        import aituber.api.api
        aituber.api.api.tuber_app = mock_app_services
        
        yield TestClient(app)


def test_text_chat_integration(client):
    """テキスト対話の統合テスト"""
    response = client.post("/chat", json={
        "character_id": "test_char",
        "user_id": "test_user",
        "message": "こんにちは",
        "response_type": "text"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert "text" in data
    assert data["text"] == "テスト応答"


def test_audio_chat_integration(client):
    """音声対話の統合テスト"""
    response = client.post("/chat", json={
        "character_id": "test_char",
        "user_id": "test_user",
        "message": "音声で返答して",
        "response_type": "audio"
    })
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert "x-conversation-id" in response.headers
    assert len(response.content) > 0


def test_text_to_speech_integration(client):
    """テキスト→音声変換の統合テスト"""
    # 通常のチャットでaudio指定をテスト
    response = client.post("/chat", json={
        "character_id": "test_char",
        "user_id": "test_user",
        "message": "テキストから音声に変換してください",
        "response_type": "audio"
    })
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert "x-conversation-id" in response.headers
    assert len(response.content) > 0


def test_stream_chat_integration(client):
    """ストリーミング対話の統合テスト"""
    response = client.post("/chat/stream", json={
        "character_id": "test_char",
        "user_id": "test_user",
        "message": "ストリーミングで返答して"
    })
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    
    # ストリーミングデータの確認
    content = response.content.decode("utf-8")
    assert "テスト" in content
    assert "応答" in content
    assert "です" in content


def test_characters_list_integration(client):
    """キャラクター一覧の統合テスト"""
    response = client.get("/characters")
    
    assert response.status_code == 200
    data = response.json()
    assert "characters" in data
    assert len(data["characters"]) > 0
    
    char = data["characters"][0]
    assert char["id"] == "test_char"
    assert char["name"] == "テストキャラ"
    assert "description" in char


def test_conversation_history_integration(client):
    """会話履歴の統合テスト"""
    response = client.get("/conversations/test-conv-123/history")
    
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert "history" in data
    assert data["conversation_id"] == "test-conv-123"


def test_invalid_character_integration(client):
    """存在しないキャラクターでのエラーテスト"""
    response = client.post("/chat", json={
        "character_id": "nonexistent",
        "user_id": "test_user",
        "message": "テスト",
        "response_type": "text"
    })
    
    assert response.status_code == 404
    assert "キャラクターが見つかりません" in response.json()["detail"]


def test_validation_error_integration(client):
    """バリデーションエラーのテスト"""
    # 必須フィールドの欠如
    response = client.post("/chat", json={
        "character_id": "test_char",
        # user_idとmessageが欠如
        "response_type": "text"
    })
    
    assert response.status_code == 422