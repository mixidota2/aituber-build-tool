"""シンプルなサービスコンテナの実装"""

from typing import Optional

from .config import AITuberConfig
from .services.llm.openai import OpenAIService
from .services.memory.chromadb import ChromaDBMemoryService
from .services.storage.local import LocalStorageService
from .services.character import CharacterService
from .services.conversation import ConversationService
from .services.storage.character import FileSystemCharacterStorage


class ServiceContainer:
    """シンプルなサービスコンテナ"""

    def __init__(self, config: AITuberConfig):
        """
        サービスコンテナの初期化

        Args:
            config: アプリケーション設定
        """
        self.config = config
        self._llm_service: Optional[OpenAIService] = None
        self._storage_service: Optional[LocalStorageService] = None
        self._memory_service: Optional[ChromaDBMemoryService] = None
        self._character_service: Optional[CharacterService] = None
        self._conversation_service: Optional[ConversationService] = None
        self._character_storage: Optional[FileSystemCharacterStorage] = None

    @property
    def llm_service(self) -> OpenAIService:
        """LLMサービスのシングルトンインスタンスを取得"""
        if self._llm_service is None:
            self._llm_service = OpenAIService(self.config)
        return self._llm_service

    @property
    def storage_service(self) -> LocalStorageService:
        """ストレージサービスのシングルトンインスタンスを取得"""
        if self._storage_service is None:
            self._storage_service = LocalStorageService(self.config)
        return self._storage_service

    @property
    def character_storage(self) -> FileSystemCharacterStorage:
        """キャラクターストレージのシングルトンインスタンスを取得"""
        if self._character_storage is None:
            self._character_storage = FileSystemCharacterStorage(
                str(self.config.character.characters_dir)
            )
        return self._character_storage

    @property
    def memory_service(self) -> ChromaDBMemoryService:
        """メモリサービスのシングルトンインスタンスを取得"""
        if self._memory_service is None:
            self._memory_service = ChromaDBMemoryService(
                config=self.config, llm_service=self.llm_service
            )
        return self._memory_service

    @property
    def character_service(self) -> CharacterService:
        """キャラクターサービスのシングルトンインスタンスを取得"""
        if self._character_service is None:
            self._character_service = CharacterService(
                config=self.config, storage=self.character_storage
            )
        return self._character_service

    @property
    def conversation_service(self) -> ConversationService:
        """会話サービスのシングルトンインスタンスを取得"""
        if self._conversation_service is None:
            self._conversation_service = ConversationService(
                config=self.config,
                character_service=self.character_service,
                memory_service=self.memory_service,
                llm_service=self.llm_service,
            )
        return self._conversation_service
