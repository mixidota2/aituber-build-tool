"""キャラクターローディングのテスト"""

import pytest
import tempfile
import os
import yaml
from pathlib import Path
from unittest.mock import patch, AsyncMock, Mock

from aituber.api.api import get_character, get_character_dir, list_characters
from aituber.core.models.character import Character


@pytest.fixture
def test_character_data():
    """テスト用キャラクターデータ"""
    return {
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
        "personality_traits": [
            {
                "name": "親切",
                "description": "親切な性格",
                "score": 0.8
            }
        ],
        "interests": [
            {
                "name": "プログラミング",
                "description": "プログラミングが好き",
                "level": 0.9
            }
        ],
        "voicevox": {
            "style_id": 1
        }
    }


@pytest.fixture
def temp_character_dir(test_character_data):
    """一時的なキャラクターディレクトリを作成"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        char_dir = Path(tmp_dir) / "characters"
        char_dir.mkdir()
        
        # テストキャラクターファイルを作成
        char_file = char_dir / "test_char.yaml"
        with open(char_file, "w", encoding="utf-8") as f:
            yaml.dump(test_character_data, f, allow_unicode=True)
        
        yield str(char_dir)


@pytest.mark.asyncio
async def test_get_character_dir_with_app():
    """get_character_dir関数のテスト（アプリ設定あり）"""
    mock_app = Mock()
    mock_app.config.app.data_dir = "/test/data"
    mock_app.config.character.characters_dir = "characters"
    
    with patch("aituber.api.api.tuber_app", mock_app):
        result = get_character_dir()
        assert result == "/test/data/characters"


def test_get_character_dir_fallback():
    """get_character_dir関数のテスト（フォールバック）"""
    with patch("aituber.api.api.tuber_app", None):
        result = get_character_dir()
        expected = os.path.join(os.getcwd(), "data", "characters")
        assert result == expected


@pytest.mark.asyncio
async def test_get_character_with_service(test_character_data):
    """CharacterServiceを使用したキャラクター取得のテスト"""
    mock_app = Mock()
    mock_character_service = Mock()
    mock_character = Character(**test_character_data)
    
    # 非同期メソッドのモック
    mock_character_service.load_character = AsyncMock(return_value=mock_character)
    mock_app.character_service = mock_character_service
    
    with patch("aituber.api.api.tuber_app", mock_app), \
         patch("aituber.api.api.get_app", return_value=mock_app):
        
        result = await get_character("test_char")
        assert result.id == "test_char"
        assert result.name == "テストキャラ"
        mock_character_service.load_character.assert_called_once_with("test_char")


@pytest.mark.asyncio
async def test_get_character_fallback(temp_character_dir, test_character_data):
    """ファイルシステムフォールバックでのキャラクター取得テスト"""
    mock_app = Mock()
    mock_character_service = Mock()
    
    # CharacterServiceでエラーが発生する設定
    mock_character_service.load_character = AsyncMock(side_effect=Exception("Service error"))
    mock_app.character_service = mock_character_service
    
    with patch("aituber.api.api.tuber_app", mock_app), \
         patch("aituber.api.api.get_app", return_value=mock_app), \
         patch("aituber.api.api.get_character_dir", return_value=temp_character_dir):
        
        result = await get_character("test_char")
        assert result.id == "test_char"
        assert result.name == "テストキャラ"


@pytest.mark.asyncio
async def test_get_character_not_found():
    """存在しないキャラクターのテスト"""
    mock_app = Mock()
    mock_character_service = Mock()
    
    # CharacterServiceでエラーが発生し、ファイルも存在しない
    mock_character_service.load_character = AsyncMock(side_effect=Exception("Not found"))
    mock_app.character_service = mock_character_service
    
    with patch("aituber.api.api.tuber_app", mock_app), \
         patch("aituber.api.api.get_app", return_value=mock_app), \
         patch("aituber.api.api.get_character_dir", return_value="/nonexistent"):
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_character("nonexistent")
        
        assert exc_info.value.status_code == 404
        assert "キャラクターが見つかりません" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_list_characters_with_service():
    """CharacterServiceを使用したキャラクター一覧取得のテスト"""
    mock_app = Mock()
    mock_character_service = Mock()
    
    # テストキャラクターデータ
    test_chars = [
        Character(
            id="char1",
            name="キャラ1",
            description="説明1",
            system_prompt="プロンプト1",
            persona={},
            personality_traits=[],
            interests=[]
        ),
        Character(
            id="char2", 
            name="キャラ2",
            description="とても長い説明" * 20,  # 200文字を超える説明
            system_prompt="プロンプト2",
            persona={},
            personality_traits=[],
            interests=[]
        )
    ]
    
    mock_character_service.list_characters = Mock(return_value=test_chars)
    mock_app.character_service = mock_character_service
    
    with patch("aituber.api.api.tuber_app", mock_app), \
         patch("aituber.api.api.get_app", return_value=mock_app):
        
        result = await list_characters()
        
        assert len(result.characters) == 2
        assert result.characters[0]["id"] == "char1"
        assert result.characters[0]["name"] == "キャラ1"
        assert result.characters[1]["description"].endswith("...")  # 長い説明は省略される


@pytest.mark.asyncio
async def test_list_characters_fallback(temp_character_dir):
    """ファイルシステムフォールバックでのキャラクター一覧取得テスト"""
    mock_app = Mock()
    mock_character_service = Mock()
    
    # CharacterServiceでエラーが発生する設定
    mock_character_service.list_characters = Mock(side_effect=Exception("Service error"))
    mock_app.character_service = mock_character_service
    
    with patch("aituber.api.api.tuber_app", mock_app), \
         patch("aituber.api.api.get_app", return_value=mock_app), \
         patch("aituber.api.api.get_character_dir", return_value=temp_character_dir):
        
        result = await list_characters()
        
        assert len(result.characters) == 1
        assert result.characters[0]["id"] == "test_char"
        assert result.characters[0]["name"] == "テストキャラ"


@pytest.mark.asyncio 
async def test_list_characters_empty_directory():
    """空のディレクトリでのキャラクター一覧取得テスト"""
    mock_app = Mock()
    mock_character_service = Mock()
    
    # CharacterServiceでエラーが発生し、空のディレクトリ
    mock_character_service.list_characters = Mock(side_effect=Exception("Service error"))
    mock_app.character_service = mock_character_service
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        with patch("aituber.api.api.tuber_app", mock_app), \
             patch("aituber.api.api.get_app", return_value=mock_app), \
             patch("aituber.api.api.get_character_dir", return_value=tmp_dir):
            
            result = await list_characters()
            assert len(result.characters) == 0