"""Character manager for AITuber framework."""

from typing import Dict, Any, List, Optional, Union
from pydantic import ValidationError

from .models import Character
from .storage import CharacterStorage
from ..core.context import AppContext
from ..core.events import EventType
from ..core.exceptions import CharacterError


class CharacterManager:
    """キャラクター設定の管理を行うクラス"""

    def __init__(self, app_context: AppContext, storage: CharacterStorage):
        self.app_context = app_context
        self.storage = storage
        self.active_character: Optional[Character] = None
        self.loaded_characters: Dict[str, Character] = {}

    def load_character(self, character_id: str) -> Character:
        """キャラクター設定を読み込む"""
        # すでに読み込まれている場合はキャッシュから返す
        if character_id in self.loaded_characters:
            return self.loaded_characters[character_id]

        # ストレージから読み込む
        try:
            character_data = self.storage.get_character(character_id)
            character = Character.model_validate(character_data)
            self.loaded_characters[character_id] = character

            # イベント発行
            self.app_context.publish_event(
                EventType.CHARACTER_LOADED,
                data={"character_id": character_id},
                source="character_manager",
            )

            return character
        except Exception as e:
            raise CharacterError(
                f"キャラクター '{character_id}' の読み込みに失敗しました: {e}"
            )

    def set_active_character(self, character_id: str) -> Character:
        """アクティブなキャラクターを設定する"""
        character = self.load_character(character_id)
        previous_character_id = (
            self.active_character.id if self.active_character else None
        )
        self.active_character = character

        # イベント発行
        self.app_context.publish_event(
            EventType.CHARACTER_SWITCHED,
            data={
                "previous_character_id": previous_character_id,
                "new_character_id": character_id,
            },
            source="character_manager",
        )

        return character

    def get_active_character(self) -> Optional[Character]:
        """現在アクティブなキャラクターを取得する"""
        return self.active_character

    def create_character(
        self, character_data: Union[Dict[str, Any], Character]
    ) -> Character:
        """新しいキャラクターを作成する"""
        try:
            # Characterオブジェクトの場合はそのまま使用
            if isinstance(character_data, Character):
                character = character_data
            else:
                # 辞書の場合はバリデーション
                character = Character.model_validate(character_data)

            # IDが既に存在するか確認
            if character.id in self.list_character_ids():
                raise CharacterError(
                    f"キャラクターID '{character.id}' は既に存在します"
                )

            # 保存
            self.storage.save_character(character.id, character.model_dump())
            self.loaded_characters[character.id] = character

            return character
        except ValidationError as e:
            raise CharacterError(f"キャラクターデータが無効です: {e}")
        except Exception as e:
            raise CharacterError(f"キャラクターの作成に失敗しました: {e}")

    def update_character(
        self, character_id: str, character_data: Union[Dict[str, Any], Character]
    ) -> Character:
        """キャラクター設定を更新する"""
        try:
            # キャラクターが存在するか確認
            if character_id not in self.list_character_ids():
                raise CharacterError(
                    f"キャラクターID '{character_id}' が見つかりません"
                )

            # Characterオブジェクトの場合はそのまま使用
            if isinstance(character_data, Character):
                character = character_data
                # IDが一致するか確認
                if character.id != character_id:
                    character.id = character_id  # IDを強制的に一致させる
            else:
                # 辞書の場合はバリデーション
                character_data["id"] = character_id  # IDを強制的に一致させる
                character = Character.model_validate(character_data)

            # 保存
            self.storage.save_character(character_id, character.model_dump())
            self.loaded_characters[character_id] = character

            # アクティブキャラクターが更新された場合は更新
            if self.active_character and self.active_character.id == character_id:
                self.active_character = character

            return character
        except ValidationError as e:
            raise CharacterError(f"キャラクターデータが無効です: {e}")
        except Exception as e:
            raise CharacterError(f"キャラクターの更新に失敗しました: {e}")

    def delete_character(self, character_id: str) -> None:
        """キャラクターを削除する"""
        try:
            # キャラクターが存在するか確認
            if character_id not in self.list_character_ids():
                raise CharacterError(
                    f"キャラクターID '{character_id}' が見つかりません"
                )

            # アクティブキャラクターの場合は解除
            if self.active_character and self.active_character.id == character_id:
                self.active_character = None

            # キャッシュから削除
            if character_id in self.loaded_characters:
                del self.loaded_characters[character_id]

            # ストレージから削除
            self.storage.delete_character(character_id)
        except Exception as e:
            raise CharacterError(f"キャラクターの削除に失敗しました: {e}")

    def list_character_ids(self) -> List[str]:
        """利用可能なキャラクターIDのリストを取得する"""
        return self.storage.list_characters()

    def list_characters(self) -> List[Character]:
        """利用可能なキャラクター一覧を取得する"""
        character_ids = self.list_character_ids()
        characters = []

        for character_id in character_ids:
            try:
                character = self.load_character(character_id)
                characters.append(character)
            except CharacterError:
                # 読み込みに失敗したキャラクターはスキップ
                continue

        return characters
