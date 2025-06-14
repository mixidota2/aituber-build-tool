"""キャラクター管理サービスの実装"""

import logging
from typing import Dict, Any, List, Optional

from ..config import AITuberConfig
from ..exceptions import CharacterError
from ..models.character import Character, Persona, PersonalityTrait, Interest
from .storage.character import FileSystemCharacterStorage

logger = logging.getLogger(__name__)


class CharacterService:
    """キャラクター管理サービス"""

    def __init__(self, config: AITuberConfig, storage: FileSystemCharacterStorage):
        self.config = config
        self.storage = storage
        self.characters: Dict[str, Character] = {}
        # Note: _load_characters is now async and should be called separately

    async def _load_characters(self) -> None:
        """キャラクターファイルを読み込む"""
        try:
            characters = await self.storage.load_all()
            self.characters = {character.id: character for character in characters}
            logger.info(f"Loaded {len(self.characters)} characters successfully")
        except Exception as e:
            logger.error(f"Failed to load characters: {e}")
            # Don't raise exception here to allow graceful degradation
            self.characters = {}

    async def create_character(
        self,
        name: str,
        description: str,
        system_prompt: str,
        persona: Persona,
        personality_traits: Optional[List[PersonalityTrait]] = None,
        interests: Optional[List[Interest]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Character:
        """新しいキャラクターを作成"""
        try:
            character = Character(
                id=name.lower().replace(" ", "_"),
                name=name,
                description=description,
                system_prompt=system_prompt,
                persona=persona,
                personality_traits=personality_traits or [],
                interests=interests or [],
                metadata=metadata or {},
            )
            await self.storage.save(character)
            self.characters[character.id] = character
            return character
        except Exception as e:
            raise CharacterError(f"キャラクターの作成中にエラーが発生しました: {e}")

    def get_character(self, character_id: str) -> Character:
        """キャラクターを取得"""
        if character_id not in self.characters:
            raise CharacterError(f"キャラクターが見つかりません: {character_id}")
        return self.characters[character_id]

    async def update_character(self, character_id: str, updates: Dict[str, Any]) -> Character:
        """キャラクター情報を更新"""
        character = self.get_character(character_id)
        try:
            for key, value in updates.items():
                if hasattr(character, key):
                    setattr(character, key, value)
            await self.storage.save(character)
            return character
        except Exception as e:
            raise CharacterError(f"キャラクターの更新中にエラーが発生しました: {e}")

    async def delete_character(self, character_id: str) -> None:
        """キャラクターを削除"""
        if character_id in self.characters:
            self.storage.delete(character_id)
            del self.characters[character_id]

    def list_characters(self) -> List[Character]:
        """全キャラクターのリストを取得"""
        return list(self.characters.values())

    async def load_character(self, character_id: str) -> Character:
        """キャラクターをロード"""
        if character_id not in self.characters:
            try:
                character = await self.storage.load(character_id)
                self.characters[character.id] = character
            except Exception as e:
                raise CharacterError(f"Failed to load character {character_id}: {e}")
        return self.get_character(character_id)
