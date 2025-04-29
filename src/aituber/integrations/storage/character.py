"""キャラクターストレージの実装"""

import os
import json
import yaml
from typing import List

from ...core.models.character import Character
from ...core.exceptions import CharacterError
from ...core.config import resolve_data_path

class FileSystemCharacterStorage:
    """ファイルシステムベースのキャラクターストレージ"""

    def __init__(self, data_dir: str, characters_dir: str = "characters"):
        """
        初期化
        
        Args:
            data_dir: データディレクトリのパス
            characters_dir: キャラクターデータを格納するディレクトリ（data_dirからの相対パス）
        """
        self.base_dir = resolve_data_path(data_dir, characters_dir)
        try:
            os.makedirs(self.base_dir, exist_ok=True)
        except Exception as e:
            raise CharacterError(f"ストレージの初期化に失敗しました: {e}")

    def save(self, character: Character) -> None:
        """キャラクターをファイルに保存"""
        try:
            if not os.path.exists(self.base_dir) or not os.access(self.base_dir, os.W_OK):
                raise CharacterError(f"保存先ディレクトリにアクセスできません: {self.base_dir}")
            
            if not character.id:
                raise ValueError("キャラクターIDが空です")

            file_path = os.path.join(self.base_dir, f"{character.id}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(character.model_dump(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise CharacterError(f"キャラクターの保存中にエラーが発生しました: {e}")

    def load(self, character_id: str) -> Character:
        """キャラクターをファイルから読み込む"""
        try:
            # まずJSONファイルを探す
            json_path = os.path.join(self.base_dir, f"{character_id}.json")
            yaml_path = os.path.join(self.base_dir, f"{character_id}.yaml")
            
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return Character.model_validate(data)
            elif os.path.exists(yaml_path):
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    return Character.model_validate(data)
            else:
                raise CharacterError(f"キャラクターファイルが見つかりません: {character_id}")

        except Exception as e:
            raise CharacterError(f"キャラクターの読み込み中にエラーが発生しました: {e}")

    def load_all(self) -> List[Character]:
        """すべてのキャラクターを読み込む"""
        characters = []
        if not os.path.exists(self.base_dir):
            return characters

        for filename in os.listdir(self.base_dir):
            if filename.endswith((".json", ".yaml")):
                try:
                    character_id = os.path.splitext(filename)[0]
                    character = self.load(character_id)
                    characters.append(character)
                except Exception as e:
                    print(f"キャラクターの読み込みに失敗しました {filename}: {e}")

        return characters

    def list_characters(self) -> List[str]:
        """保存されているキャラクターのIDリストを取得"""
        try:
            if not os.path.exists(self.base_dir):
                return []

            files = os.listdir(self.base_dir)
            return [
                os.path.splitext(f)[0]
                for f in files
                if f.endswith((".json", ".yaml"))
            ]
        except Exception as e:
            raise CharacterError(f"キャラクターリストの取得中にエラーが発生しました: {e}")

    def delete(self, character_id: str) -> None:
        """キャラクターファイルを削除"""
        try:
            json_path = os.path.join(self.base_dir, f"{character_id}.json")
            yaml_path = os.path.join(self.base_dir, f"{character_id}.yaml")
            
            if os.path.exists(json_path):
                os.remove(json_path)
            if os.path.exists(yaml_path):
                os.remove(yaml_path)
        except Exception as e:
            raise CharacterError(f"キャラクターの削除中にエラーが発生しました: {e}")

    def exists(self, character_id: str) -> bool:
        """キャラクターファイルの存在確認"""
        if not character_id:
            return False
        json_path = os.path.join(self.base_dir, f"{character_id}.json")
        yaml_path = os.path.join(self.base_dir, f"{character_id}.yaml")
        return os.path.exists(json_path) or os.path.exists(yaml_path) 