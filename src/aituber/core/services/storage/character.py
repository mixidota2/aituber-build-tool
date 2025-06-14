"""キャラクターストレージの実装"""

import os
import yaml
import logging
import aiofiles
from pathlib import Path
from typing import List

from ....core.exceptions import CharacterError
from ....core.models.character import Character

logger = logging.getLogger(__name__)


class FileSystemCharacterStorage:
    """ファイルシステムを使用したキャラクターストレージ"""

    def __init__(self, base_dir: str | Path):
        """初期化

        Args:
            base_dir: キャラクターファイルの保存先ディレクトリ
        """
        self.base_dir = Path(base_dir)
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """保存先ディレクトリの存在確認と作成"""
        try:
            os.makedirs(self.base_dir, exist_ok=True)
        except Exception as e:
            raise CharacterError(f"保存先ディレクトリにアクセスできません: {e}")

    def _get_character_path(self, character_id: str) -> Path:
        """キャラクターファイルのパスを取得"""
        return self.base_dir / f"{character_id}.yaml"

    async def save(self, character: Character) -> None:
        """キャラクターを保存"""
        try:
            file_path = self._get_character_path(character.id)
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                content = yaml.dump(
                    character.model_dump(), allow_unicode=True, sort_keys=False
                )
                await f.write(content)
        except Exception as e:
            raise CharacterError(f"キャラクターの保存に失敗しました: {e}")

    async def load(self, character_id: str) -> Character:
        """キャラクターを読み込む"""
        file_path = self._get_character_path(character_id)
        if not file_path.exists():
            raise CharacterError(
                f"キャラクターファイルが見つかりません: {character_id}"
            )

        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = yaml.safe_load(content)
                return Character.model_validate(data)
        except Exception as e:
            raise CharacterError(f"キャラクターの読み込みに失敗しました: {e}")

    async def load_all(self) -> List[Character]:
        """全てのキャラクターを読み込む"""
        characters = []
        for file_path in self.base_dir.glob("*.yaml"):
            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                    data = yaml.safe_load(content)
                    characters.append(Character.model_validate(data))
            except Exception as e:
                logger.warning(f"Failed to load character from {file_path}: {e}")
        return characters

    def list_characters(self) -> List[str]:
        """キャラクターIDの一覧を取得"""
        return [file_path.stem for file_path in self.base_dir.glob("*.yaml")]

    def delete(self, character_id: str) -> None:
        """キャラクターを削除"""
        file_path = self._get_character_path(character_id)
        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception as e:
                raise CharacterError(f"キャラクターの削除に失敗しました: {e}")
