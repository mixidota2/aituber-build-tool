import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import yaml
import io
from pathlib import Path
from aituber.api.api import app


@pytest.fixture
def test_character_dir():
    """テスト用のキャラクターディレクトリを作成"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        char_dir = Path(tmp_dir) / "characters"
        char_dir.mkdir()
        
        # テスト用キャラクターファイルを作成
        char_data = {
            "id": "railly",
            "name": "らいりぃ",
            "description": "テスト用キャラクター",
            "system_prompt": "あなたは「らいりぃ」というAIキャラクターです。",
            "persona": {
                "age": 18,
                "gender": "中性的",
                "occupation": "学生",
                "background": "普通の学生",
                "appearance": "青髪に猫耳ヘッドホン",
                "speech_style": "砕けた口調"
            },
            "personality_traits": [],
            "interests": [],
            "voicevox": {
                "style_id": 1
            }
        }
        
        char_file = char_dir / "railly.yaml"
        with open(char_file, "w", encoding="utf-8") as f:
            yaml.dump(char_data, f, allow_unicode=True)
        
        yield str(char_dir)


@pytest.fixture
def mock_app_services():
    """アプリケーションサービスをモック"""
    mock_app = Mock()
    mock_conversation_service = Mock()
    mock_tts_service = Mock()
    mock_character_service = Mock()
    
    # キャラクターサービスのモック（存在しないキャラクターでエラーを発生させる）
    from aituber.core.exceptions import CharacterError
    mock_character_service.load_character = AsyncMock(side_effect=CharacterError("Character not found"))
    
    # 会話サービスのモック
    mock_conversation = Mock()
    mock_conversation.conversation_id = "test-conversation-123"
    mock_conversation_service.get_or_create_conversation = Mock(return_value=mock_conversation)
    mock_conversation_service.process_message = AsyncMock(return_value="これはテスト用のダミー応答です。by らいりぃ")
    
    # ストリーミングのモック
    async def mock_stream():
        chunks = ["これは", "テスト用の", "ダミー応答です。"]
        for chunk in chunks:
            yield chunk
    
    mock_conversation_service.process_message_stream = AsyncMock(side_effect=lambda *args, **kwargs: mock_stream())
    
    # TTSサービスのモック（最小限のWAVデータ）
    wav_data = b"RIFF\x24\x00\x00\x00WAVE" + b"fmt \x10\x00\x00\x00" + b"\x00" * 16
    mock_tts_service.synthesize = Mock(return_value=wav_data)
    
    mock_app.conversation_service = mock_conversation_service
    mock_app.tts_service = mock_tts_service
    mock_app.character_service = mock_character_service
    
    return mock_app


@pytest.fixture
def client(test_character_dir, mock_app_services):
    """テスト用クライアント"""
    with patch("aituber.core.character_utils.CharacterUtils.get_character_dir", return_value=test_character_dir), \
         patch("aituber.core.app_factory.AppFactory.get_app", return_value=mock_app_services):
        
        # グローバル変数の初期化
        import aituber.api.api
        aituber.api.api.tuber_app = mock_app_services
        
        yield TestClient(app)


class TestChatAPI:
    """チャットAPIのテストクラス"""
    
    def test_new_conversation_text(self, client):
        """新規会話でテキスト応答のテスト"""
        response = client.post("/chat", json={
            "character_id": "railly",
            "user_id": "testuser",
            "conversation_id": None,
            "message": "こんにちは",
            "response_type": "text"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "text" in data
        assert "らいりぃ" in data["text"]
        assert data["conversation_id"] == "test-conversation-123"
    
    def test_continue_conversation_text(self, client):
        """既存会話の継続テスト"""
        response = client.post("/chat", json={
            "character_id": "railly",
            "user_id": "testuser",
            "conversation_id": "existing-conversation-456",
            "message": "元気ですか？",
            "response_type": "text"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "text" in data
        assert "らいりぃ" in data["text"]
    
    def test_new_conversation_audio(self, client):
        """新規会話で音声応答のテスト"""
        response = client.post("/chat", json={
            "character_id": "railly",
            "user_id": "testuser",
            "conversation_id": None,
            "message": "音声で返して",
            "response_type": "audio"
        })
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"
        assert "x-conversation-id" in response.headers
        assert response.headers["x-conversation-id"] == "test-conversation-123"
        assert len(response.content) > 0
    
    def test_invalid_character(self, client):
        """存在しないキャラクターのエラーテスト"""
        response = client.post("/chat", json={
            "character_id": "nonexistent",
            "user_id": "testuser",
            "message": "テスト",
            "response_type": "text"
        })
        
        assert response.status_code == 404
        assert "キャラクターが見つかりません" in response.json()["detail"]
    
    def test_invalid_response_type(self, client):
        """無効なレスポンスタイプのバリデーションエラーテスト"""
        response = client.post("/chat", json={
            "character_id": "railly",
            "user_id": "testuser",
            "message": "テスト",
            "response_type": "invalid_type"
        })
        
        assert response.status_code == 422


class TestTextToSpeechAPI:
    """テキスト→音声変換APIのテストクラス"""
    
    def test_text_to_speech_basic(self, client):
        """基本的なテキスト→音声変換テスト"""
        response = client.post("/chat/text-to-speech", json={
            "character_id": "railly",
            "user_id": "testuser",
            "message": "テキストを音声に変換してください"
        })
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"
        assert "x-conversation-id" in response.headers
        assert "x-response-length" in response.headers
        assert len(response.content) > 0
    
    def test_text_to_speech_invalid_character(self, client):
        """存在しないキャラクターでのエラーテスト"""
        response = client.post("/chat/text-to-speech", json={
            "character_id": "nonexistent",
            "user_id": "testuser",
            "message": "エラーテスト"
        })
        
        assert response.status_code == 404
        assert "キャラクターが見つかりません" in response.json()["detail"]


class TestStreamingAPI:
    """ストリーミングAPIのテストクラス"""
    
    def test_stream_chat(self, client):
        """ストリーミングチャットのテスト"""
        response = client.post("/chat/stream", json={
            "character_id": "railly",
            "user_id": "testuser",
            "message": "ストリーミングで返答して"
        })
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        content = response.content.decode("utf-8")
        assert len(content) > 0


class TestVoiceChatAPI:
    """音声チャットAPIのテストクラス"""
    
    def test_voice_chat_valid_audio(self, client):
        """有効な音声ファイルでの音声チャットテスト"""
        audio_data = b"RIFF\x24\x00\x00\x00WAVE" + b"fmt \x10\x00\x00\x00" + b"\x00" * 20
        audio_file = io.BytesIO(audio_data)
        
        response = client.post(
            "/chat/voice",
            files={"audio": ("test.wav", audio_file, "audio/wav")},
            data={
                "character_id": "railly",
                "user_id": "testuser"
            }
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"
        assert "x-conversation-id" in response.headers
    
    def test_voice_chat_invalid_file_type(self, client):
        """無効なファイルタイプでのエラーテスト"""
        text_file = io.BytesIO(b"This is not audio")
        
        response = client.post(
            "/chat/voice",
            files={"audio": ("test.txt", text_file, "text/plain")},
            data={
                "character_id": "railly",
                "user_id": "testuser"
            }
        )
        
        assert response.status_code == 400
        assert "音声ファイルを送信してください" in response.json()["detail"]


class TestUtilityAPI:
    """ユーティリティAPIのテストクラス"""
    
    def test_characters_list(self, client):
        """キャラクター一覧取得のテスト"""
        response = client.get("/characters")
        
        assert response.status_code == 200
        data = response.json()
        assert "characters" in data
        assert len(data["characters"]) > 0
        
        char_ids = [char["id"] for char in data["characters"]]
        assert "railly" in char_ids
    
    def test_conversation_history(self, client):
        """会話履歴取得のテスト"""
        conversation_id = "test-history-123"
        response = client.get(f"/conversations/{conversation_id}/history")
        
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "history" in data
        assert data["conversation_id"] == conversation_id
    
    def test_debug_character_dir(self, client):
        """デバッグ用キャラクターディレクトリ情報取得のテスト"""
        response = client.get("/debug/character-dir")
        
        assert response.status_code == 200
        data = response.json()
        assert "character_dir" in data
        assert "exists" in data
        assert "files" in data
        assert data["exists"] is True
        assert "railly.yaml" in data["files"]
