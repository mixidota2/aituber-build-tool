"""キャラクター管理の共通ユーティリティ"""

import os
import yaml
from typing import List, Dict, Any
from pathlib import Path

from .models.character import Character
from .exceptions import CharacterError
from ..app import AITuberApp


class CharacterUtils:
    """キャラクター管理の共通機能を提供するユーティリティクラス"""
    
    @staticmethod
    async def get_character_safe(app: AITuberApp, character_id: str) -> Character:
        """
        フォールバック機能付きの安全なキャラクター取得
        
        Args:
            app: AITuberアプリケーションインスタンス
            character_id: キャラクターID
            
        Returns:
            Character: キャラクターオブジェクト
            
        Raises:
            CharacterError: キャラクターが見つからない場合
        """
        try:
            # 最初にCharacterServiceを使用
            return await app.character_service.load_character(character_id)
        except Exception:
            # フォールバック: 直接ファイルシステムから読み込み
            return await CharacterUtils._load_character_from_file(app, character_id)
    
    @staticmethod
    async def _load_character_from_file(app: AITuberApp, character_id: str) -> Character:
        """ファイルシステムから直接キャラクターを読み込み"""
        character_dir = CharacterUtils.get_character_dir(app)
        char_path = Path(character_dir) / f"{character_id}.yaml"
        
        if not char_path.exists():
            raise CharacterError(f"Character file not found: {char_path}")
        
        try:
            with open(char_path, "r", encoding="utf-8") as f:
                char_data = yaml.safe_load(f)
            return Character(**char_data)
        except Exception as e:
            raise CharacterError(f"Failed to load character from file {char_path}: {e}")
    
    @staticmethod
    def get_character_dir(app: AITuberApp) -> str:
        """
        キャラクターディレクトリのパスを取得
        
        Args:
            app: AITuberアプリケーションインスタンス
            
        Returns:
            str: キャラクターディレクトリのパス
        """
        try:
            # アプリケーション設定からパスを取得
            base_dir = app.config.app.data_dir
            char_dir = app.config.character.characters_dir
            return str(Path(base_dir) / char_dir)
        except Exception:
            # フォールバック: 現在のディレクトリからの相対パス
            return str(Path.cwd() / "data" / "characters")
    
    @staticmethod
    async def list_characters_safe(app: AITuberApp) -> List[Dict[str, Any]]:
        """
        フォールバック機能付きの安全なキャラクター一覧取得
        
        Args:
            app: AITuberアプリケーションインスタンス
            
        Returns:
            List[Dict[str, Any]]: キャラクター情報のリスト
        """
        try:
            # 最初にCharacterServiceを使用
            characters_list = app.character_service.list_characters()
            
            characters = []
            for character in characters_list:
                characters.append({
                    "id": character.id,
                    "name": character.name,
                    "description": CharacterUtils._truncate_description(character.description)
                })
            return characters
        except Exception:
            # フォールバック: 直接ファイルシステムから読み込み
            return CharacterUtils._list_characters_from_files(app)
    
    @staticmethod
    def _list_characters_from_files(app: AITuberApp) -> List[Dict[str, Any]]:
        """ファイルシステムから直接キャラクター一覧を取得"""
        characters: List[Dict[str, Any]] = []
        character_dir = CharacterUtils.get_character_dir(app)
        
        if not os.path.exists(character_dir):
            return characters
        
        for filename in os.listdir(character_dir):
            if filename.endswith(".yaml"):
                char_id = filename[:-5]  # .yamlを除く
                char_path = Path(character_dir) / filename
                try:
                    with open(char_path, "r", encoding="utf-8") as f:
                        char_data = yaml.safe_load(f)
                    characters.append({
                        "id": char_id,
                        "name": char_data.get("name", char_id),
                        "description": CharacterUtils._truncate_description(
                            char_data.get("description", "")
                        )
                    })
                except Exception:
                    # 破損したファイルはスキップ
                    continue
        
        return characters
    
    @staticmethod
    def _truncate_description(description: str, max_length: int = 100) -> str:
        """説明文を指定した長さで切り詰める"""
        if len(description) > max_length:
            return description[:max_length] + "..."
        return description
    
    @staticmethod
    def validate_character_id(character_id: str) -> bool:
        """キャラクターIDの妥当性をチェック"""
        if not character_id:
            return False
        # 基本的なバリデーション（英数字とアンダースコア、ハイフンのみ）
        import re
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', character_id))


# 便利な関数として公開
async def get_character_safe(app: AITuberApp, character_id: str) -> Character:
    """CharacterUtils.get_character_safeの便利関数"""
    return await CharacterUtils.get_character_safe(app, character_id)


async def list_characters_safe(app: AITuberApp) -> List[Dict[str, Any]]:
    """CharacterUtils.list_characters_safeの便利関数"""
    return await CharacterUtils.list_characters_safe(app)