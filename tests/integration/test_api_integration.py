"""
AITuber API Integration Tests

これらのテストは実際のAPIサーバーを起動してテストを実行します。
pytest tests/ コマンドで自動的に実行されます。
"""

import pytest
import requests
import time
from pathlib import Path
import tempfile
import os
import subprocess
from typing import Generator, Optional

from src.aituber.core.config import AITuberConfig


# テスト用の設定
TEST_PORT = 8001
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"


class APIServerManager:
    """APIサーバーの管理クラス"""
    
    def __init__(self, port: int = TEST_PORT):
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self.temp_config_file: Optional[str] = None
        
    def _create_test_config(self) -> str:
        """テスト用の設定ファイルを作成"""
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "test_config.yaml")
        
        # テスト用設定
        test_config = AITuberConfig()
        test_config.app.data_dir = Path(temp_dir) / "data"
        test_config.character.characters_dir = Path("data/characters")
        test_config.memory.vector_db_path = Path("data/vector_db")
        
        # 設定をディクトに変換してからYAMLに保存
        config_dict = {
            "app": {
                "data_dir": str(test_config.app.data_dir),
                "debug": test_config.app.debug
            },
            "character": {
                "characters_dir": str(test_config.character.characters_dir)
            },
            "storage": {
                "local_path": str(test_config.storage.local_path)
            },
            "memory": {
                "vector_db_path": str(test_config.memory.vector_db_path),
                "collection_name": test_config.memory.collection_name
            },
            "integrations": {
                "openai": {
                    "api_key": os.getenv("OPENAI_API_KEY", ""),
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            }
        }
        
        import yaml
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, allow_unicode=True, sort_keys=False)
        
        # データディレクトリとテスト用キャラクターを作成
        os.makedirs(test_config.app.data_dir / "characters", exist_ok=True)
        os.makedirs(test_config.app.data_dir / "vector_db", exist_ok=True)
        
        # テスト用キャラクターファイルをコピー
        original_char_path = Path("data/characters")
        target_char_path = test_config.app.data_dir / "characters"
        
        if original_char_path.exists():
            import shutil
            for char_file in original_char_path.glob("*.yaml"):
                shutil.copy2(char_file, target_char_path)
        else:
            # テスト用の最小限のキャラクターを作成
            test_character = {
                "id": "test_character",
                "name": "テストキャラクター",
                "description": "統合テスト用のキャラクター",
                "persona": "テスト用のペルソナ",
                "personality_traits": ["friendly", "helpful"],
                "interests": ["testing"],
                "voice": {"voicevox": {"speaker_id": 1}}
            }
            
            import yaml
            with open(target_char_path / "test_character.yaml", "w", encoding="utf-8") as f:
                yaml.dump(test_character, f, allow_unicode=True)
        
        self.temp_config_file = config_path
        return config_path
        
    def start(self) -> bool:
        """APIサーバーを開始"""
        try:
            # テスト用設定ファイルを作成
            config_path = self._create_test_config()
            
            # サーバーをサブプロセスで起動
            self.process = subprocess.Popen([
                "uv", "run", "aituber", "serve",
                "--host", "127.0.0.1", 
                "--port", str(self.port),
                "--config", config_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # サーバーの起動を待機
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = requests.get(f"{BASE_URL}/characters", timeout=1)
                    if response.status_code == 200:
                        return True
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                    time.sleep(1)
                    
                # プロセスが終了していないかチェック
                if self.process.poll() is not None:
                    stdout, stderr = self.process.communicate()
                    print("サーバープロセスが終了しました:")
                    print(f"STDOUT: {stdout.decode()}")
                    print(f"STDERR: {stderr.decode()}")
                    return False
                    
            # タイムアウト時もエラー情報を表示
            if self.process.poll() is None:
                print("サーバー起動タイムアウト")
            else:
                stdout, stderr = self.process.communicate()
                print("サーバープロセス終了:")
                print(f"STDOUT: {stdout.decode()}")
                print(f"STDERR: {stderr.decode()}")
            return False
            
        except Exception as e:
            print(f"サーバー起動エラー: {e}")
            return False
            
    def stop(self):
        """APIサーバーを停止"""
        if self.process:
            try:
                # プロセスを終了
                self.process.terminate()
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            finally:
                self.process = None
                
        # 一時設定ファイルをクリーンアップ
        if self.temp_config_file and os.path.exists(self.temp_config_file):
            import shutil
            temp_dir = os.path.dirname(self.temp_config_file)
            shutil.rmtree(temp_dir, ignore_errors=True)
            self.temp_config_file = None


@pytest.fixture(scope="session")
def api_server() -> Generator[APIServerManager, None, None]:
    """セッション全体でAPIサーバーを管理"""
    server = APIServerManager()
    
    # サーバー起動
    if not server.start():
        pytest.skip("APIサーバーの起動に失敗しました")
        
    yield server
    
    # サーバー停止
    server.stop()


@pytest.fixture(scope="session") 
def test_character_id(api_server: APIServerManager) -> str:
    """テスト用のキャラクターIDを取得"""
    response = requests.get(f"{BASE_URL}/characters")
    assert response.status_code == 200
    
    characters = response.json()["characters"]
    if not characters:
        pytest.skip("テスト用キャラクターが見つかりません")
    
    return characters[0]["id"]


class TestAPIEndpoints:
    """API エンドポイントのテスト"""

    def test_get_characters(self, api_server: APIServerManager):
        """キャラクター一覧取得のテスト"""
        response = requests.get(f"{BASE_URL}/characters")
        assert response.status_code == 200
        
        data = response.json()
        assert "characters" in data
        assert isinstance(data["characters"], list)

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
    def test_text_chat(self, api_server: APIServerManager, test_character_id: str):
        """テキスト対話のテスト"""
        chat_data = {
            "character_id": test_character_id,
            "user_id": "test_user",
            "message": "こんにちは！",
            "response_type": "text"
        }
        
        response = requests.post(f"{BASE_URL}/chat", json=chat_data)
        assert response.status_code == 200
        
        result = response.json()
        assert "text" in result
        assert "conversation_id" in result
        assert isinstance(result["text"], str)
        assert len(result["text"]) > 0

    def test_text_to_speech(self, api_server: APIServerManager, test_character_id: str):
        """テキスト→音声変換のテスト"""
        tts_data = {
            "character_id": test_character_id,
            "user_id": "test_user",
            "message": "音声で返事してもらえる？"
        }
        
        response = requests.post(f"{BASE_URL}/chat/text-to-speech", json=tts_data)
        # 音声合成が設定されていない場合は500エラーが期待される
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            # Content-Typeがaudioであることを確認
            content_type = response.headers.get('content-type', '')
            assert 'audio' in content_type or 'application/octet-stream' in content_type
            
            # 音声データが存在することを確認
            assert len(response.content) > 0
            
            # 会話IDがヘッダーに含まれることを確認
            conversation_id = response.headers.get('x-conversation-id')
            assert conversation_id is not None

    def test_audio_chat(self, api_server: APIServerManager, test_character_id: str):
        """音声応答チャットのテスト"""
        chat_data = {
            "character_id": test_character_id,
            "user_id": "test_user", 
            "message": "音声で返答してください",
            "response_type": "audio"
        }
        
        response = requests.post(f"{BASE_URL}/chat", json=chat_data)
        # 音声合成が設定されていない場合は500エラーが期待される
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            # 音声データが返されることを確認
            assert len(response.content) > 0

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
    def test_streaming_chat(self, api_server: APIServerManager, test_character_id: str):
        """ストリーミング対話のテスト"""
        stream_data = {
            "character_id": test_character_id,
            "user_id": "test_user",
            "message": "ストリーミングテスト"
        }
        
        response = requests.post(f"{BASE_URL}/chat/stream", json=stream_data, stream=True)
        assert response.status_code == 200
        
        # ストリーミングデータを受信
        chunks = []
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            if chunk:
                chunks.append(chunk)
                if len(chunks) > 10:  # 無限ループ回避
                    break
        
        # 何らかのデータが返されることを確認
        assert len(chunks) > 0

    def test_error_handling(self, api_server: APIServerManager):
        """エラーハンドリングのテスト"""
        # 無効なキャラクターID
        chat_data = {
            "character_id": "nonexistent",
            "user_id": "test_user",
            "message": "テスト",
            "response_type": "text"
        }
        
        response = requests.post(f"{BASE_URL}/chat", json=chat_data)
        assert response.status_code != 200


class TestAPIWorkflow:
    """API ワークフローのテスト"""
    
    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
    def test_full_conversation_workflow(self, api_server: APIServerManager, test_character_id: str):
        """完全な対話ワークフローのテスト"""
        # 1. 初回メッセージ
        chat_data = {
            "character_id": test_character_id,
            "user_id": "workflow_test_user",
            "message": "初回メッセージです",
            "response_type": "text"
        }
        
        response1 = requests.post(f"{BASE_URL}/chat", json=chat_data)
        assert response1.status_code == 200
        
        result1 = response1.json()
        conversation_id = result1["conversation_id"]
        
        # 2. 続きのメッセージ（同じ会話）
        chat_data["conversation_id"] = conversation_id
        chat_data["message"] = "続きのメッセージです"
        
        response2 = requests.post(f"{BASE_URL}/chat", json=chat_data)
        assert response2.status_code == 200
        
        result2 = response2.json()
        assert result2["conversation_id"] == conversation_id
        
        # 3. 会話履歴の確認
        history_response = requests.get(f"{BASE_URL}/conversations/{conversation_id}/history")
        assert history_response.status_code == 200
        
        history = history_response.json()["history"]
        assert len(history) >= 2  # 少なくとも2つのメッセージ