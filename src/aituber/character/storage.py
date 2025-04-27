"""Character storage for AITuber framework."""

from typing import Dict, Any, List
from pathlib import Path
import os
import yaml
from abc import ABC, abstractmethod

from ..core.exceptions import StorageError, CharacterError


class CharacterStorage(ABC):
    """キャラクター設定の保存と読み込みを行う抽象基底クラス"""

    @abstractmethod
    def get_character(self, character_id: str) -> Dict[str, Any]:
        """キャラクター設定を取得する"""
        pass

    @abstractmethod
    def save_character(self, character_id: str, data: Dict[str, Any]) -> None:
        """キャラクター設定を保存する"""
        pass

    @abstractmethod
    def list_characters(self) -> List[str]:
        """利用可能なキャラクターIDのリストを取得する"""
        pass

    @abstractmethod
    def delete_character(self, character_id: str) -> None:
        """キャラクター設定を削除する"""
        pass


class FileSystemCharacterStorage(CharacterStorage):
    """ファイルシステムベースのキャラクター設定ストレージ"""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def get_character_path(self, character_id: str) -> Path:
        """キャラクター設定ファイルのパスを取得"""
        return self.base_dir / f"{character_id}.yaml"

    def get_character(self, character_id: str) -> Dict[str, Any]:
        """キャラクター設定を取得する"""
        file_path = self.get_character_path(character_id)

        if not file_path.exists():
            raise CharacterError(f"キャラクター '{character_id}' が見つかりません")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise StorageError(
                f"キャラクター '{character_id}' の読み込み中にエラーが発生しました: {e}"
            )

    def save_character(self, character_id: str, data: Dict[str, Any]) -> None:
        """キャラクター設定を保存する"""
        file_path = self.get_character_path(character_id)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            raise StorageError(
                f"キャラクター '{character_id}' の保存中にエラーが発生しました: {e}"
            )

    def list_characters(self) -> List[str]:
        """利用可能なキャラクターIDのリストを取得する"""
        character_ids = []

        for file_path in self.base_dir.glob("*.yaml"):
            character_id = file_path.stem
            character_ids.append(character_id)

        return character_ids

    def delete_character(self, character_id: str) -> None:
        """キャラクター設定を削除する"""
        file_path = self.get_character_path(character_id)

        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception as e:
                raise StorageError(
                    f"キャラクター '{character_id}' の削除中にエラーが発生しました: {e}"
                )
        else:
            raise CharacterError(f"キャラクター '{character_id}' が見つかりません")
