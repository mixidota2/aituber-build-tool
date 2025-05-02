"""Application factory for AITuber framework."""

import os
from typing import Optional

from .core.config import ConfigManager
from .core.container import Container
from .core.services.character import CharacterService
from .core.services.memory import MemoryService
from .core.services.conversation import ConversationService
from .core.services.llm import LLMService

class AITuberApp:
    """AITuberアプリケーションのメインクラス"""

    def __init__(self, config_path: str = "config.yaml"):
        """
        アプリケーションの初期化

        Args:
            config_path: 設定ファイルのパス
        """
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load_config()
        self._container = Container(self.config)

    @property
    def llm_service(self) -> LLMService:
        """LLMサービスを取得する"""
        return self._container.llm_service

    @property
    def character_service(self) -> CharacterService:
        """キャラクターサービスを取得する"""
        return self._container.character_service

    @property
    def memory_service(self) -> MemoryService:
        """メモリサービスを取得する"""
        return self._container.memory_service

    @property
    def conversation_service(self) -> ConversationService:
        """会話サービスを取得する"""
        return self._container.conversation_service

    async def initialize(self) -> None:
        """アプリケーションの初期化"""
        try:
            # データディレクトリの作成
            if not os.path.exists(self.config.app.data_dir):
                os.makedirs(self.config.app.data_dir)

            # 各サービスにアクセスして初期化を行う
            _ = self.llm_service
            _ = self.character_service
            _ = self.memory_service
            _ = self.conversation_service

        except Exception as e:
            raise e


# アプリケーションのシングルトンインスタンス
_app_instance: Optional[AITuberApp] = None


async def get_app(config_path: Optional[str] = None) -> AITuberApp:
    """アプリケーションのシングルトンインスタンスを取得"""
    global _app_instance

    if _app_instance is None:
        _app_instance = AITuberApp(config_path or "config.yaml")
        await _app_instance.initialize()

    return _app_instance
