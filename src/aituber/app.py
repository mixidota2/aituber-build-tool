"""Application factory for AITuber framework."""

import os
from typing import Optional

from .core.config import ConfigManager
from .core.context import AppContext
from .core.events import EventType, Event
from .character.manager import CharacterManager
from .character.storage import FileSystemCharacterStorage
from .llm.langchain_integration import LangChainService
from .llm.conversation import ConversationManager
from .memory.manager import MemoryManager


class AITuberApp:
    """AITuberアプリケーションのメインファクトリークラス"""

    def __init__(self, config_path: Optional[str] = None):
        """
        AITuberアプリケーションの初期化

        Args:
            config_path: 設定ファイルのパス（省略時はデフォルト）
        """
        # 設定の読み込み
        config_manager = ConfigManager(config_path or "config.yaml")
        self.config = config_manager.load_config()

        # アプリケーションコンテキストの作成
        self.context = AppContext(self.config)

        # イベントリスナー登録
        self.context.event_bus.subscribe_all(self._global_event_handler)

    def _global_event_handler(self, event: Event) -> None:
        """グローバルイベントハンドラ"""
        # ここでログ出力や監視などを行うことができる
        if self.config.app.debug_mode:
            print(f"イベント: {event.type.name}, ソース: {event.source}")

    async def initialize(self) -> None:
        """アプリケーションの初期化"""
        try:
            # データディレクトリの作成
            os.makedirs(self.config.app.data_dir, exist_ok=True)

            # LangChainサービスの初期化
            langchain_service = LangChainService(self.context)
            self.context.register_service("langchain_service", langchain_service)

            # キャラクターマネージャーの初期化
            characters_dir = os.path.join(
                self.config.app.data_dir, self.config.character.characters_dir
            )
            os.makedirs(characters_dir, exist_ok=True)
            character_storage = FileSystemCharacterStorage(characters_dir)
            character_manager = CharacterManager(self.context, character_storage)
            self.context.register_service("character_manager", character_manager)

            # 会話マネージャーの初期化
            conversation_manager = ConversationManager(self.context)
            self.context.register_service("conversation_manager", conversation_manager)

            # メモリマネージャーの初期化
            memory_manager = MemoryManager(self.context)
            self.context.register_service("memory_manager", memory_manager)

            # 初期化完了イベント発行
            self.context.publish_event(
                EventType.SYSTEM_READY,
                data={"message": "AITuberアプリケーションの初期化が完了しました"},
                source="app",
            )

        except Exception as e:
            # エラーイベント発行
            self.context.publish_event(
                EventType.ERROR_OCCURRED,
                data={"error": str(e), "message": "初期化中にエラーが発生しました"},
                source="app",
            )
            raise

    def get_context(self) -> AppContext:
        """アプリケーションコンテキストの取得"""
        return self.context


# アプリケーションのシングルトンインスタンス
_app_instance: Optional[AITuberApp] = None


async def get_app(config_path: Optional[str] = None) -> AITuberApp:
    """アプリケーションのシングルトンインスタンスを取得"""
    global _app_instance

    if _app_instance is None:
        _app_instance = AITuberApp(config_path)
        await _app_instance.initialize()

    return _app_instance
