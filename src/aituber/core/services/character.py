"""キャラクター管理サービスの実装"""

from typing import Dict, Any, List, Optional

from ..config import AITuberConfig
from ..exceptions import CharacterError
from ..models.character import Character, Persona, PersonalityTrait, Interest
from ...integrations.storage.character import FileSystemCharacterStorage

class CharacterService:
    """キャラクター管理サービス"""

    def __init__(self, config: AITuberConfig, storage: FileSystemCharacterStorage):
        self.config = config
        self.storage = storage
        self.characters: Dict[str, Character] = {}
        self._load_characters()

    def _load_characters(self) -> None:
        """キャラクターファイルを読み込む"""
        try:
            characters = self.storage.load_all()
            self.characters = {character.id: character for character in characters}
        except Exception as e:
            print(f"キャラクターの読み込みに失敗しました: {e}")

    def create_character(
        self,
        name: str,
        description: str,
        system_prompt: str,
        persona: Persona,
        personality_traits: Optional[List[PersonalityTrait]] = None,
        interests: Optional[List[Interest]] = None,
        metadata: Optional[Dict[str, Any]] = None
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
                metadata=metadata or {}
            )
            self.characters[character.id] = character
            return character
        except Exception as e:
            raise CharacterError(f"キャラクターの作成中にエラーが発生しました: {e}")

    def get_character(self, character_id: str) -> Character:
        """キャラクターを取得"""
        if character_id not in self.characters:
            raise CharacterError(f"キャラクターが見つかりません: {character_id}")
        return self.characters[character_id]

    def update_character(self, character_id: str, updates: Dict[str, Any]) -> Character:
        """キャラクター情報を更新"""
        character = self.get_character(character_id)
        try:
            for key, value in updates.items():
                if hasattr(character, key):
                    setattr(character, key, value)
            return character
        except Exception as e:
            raise CharacterError(f"キャラクターの更新中にエラーが発生しました: {e}")

    def delete_character(self, character_id: str) -> None:
        """キャラクターを削除"""
        if character_id in self.characters:
            del self.characters[character_id]

    def list_characters(self) -> List[Character]:
        """全キャラクターのリストを取得"""
        return list(self.characters.values())

    def load_character(self, character_id: str) -> Character:
        """キャラクターをロード"""
        return self.get_character(character_id) 