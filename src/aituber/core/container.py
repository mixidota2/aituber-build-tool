"""DIコンテナの実装"""

from typing import Optional
from .config import AITuberConfig
from .services.character import CharacterService
from .services.conversation import ConversationService
from .services.llm import LLMService
from .services.memory import MemoryService
from ..integrations.openai.llm import OpenAILLMService
from ..integrations.storage.character import FileSystemCharacterStorage
from ..integrations.chromadb.memory import ChromaDBService


class Container:
    """シンプルなDIコンテナ"""

    def __init__(self, config: AITuberConfig):
        """
        コンテナの初期化
        
        Args:
            config: アプリケーション設定
        """
        self.config = config
        self._llm_service: Optional[LLMService] = None
        self._character_service: Optional[CharacterService] = None
        self._memory_service: Optional[MemoryService] = None
        self._conversation_service: Optional[ConversationService] = None

    @property
    def llm_service(self) -> LLMService:
        """LLMサービスの取得"""
        if self._llm_service is None:
            self._llm_service = OpenAILLMService(self.config)
        return self._llm_service

    @property
    def character_service(self) -> CharacterService:
        """キャラクターサービスの取得"""
        if self._character_service is None:
            storage = FileSystemCharacterStorage(
                data_dir=self.config.app.data_dir,
                characters_dir=self.config.character.characters_dir
            )
            self._character_service = CharacterService(self.config, storage)
        return self._character_service

    @property
    def memory_service(self) -> MemoryService:
        """メモリサービスの取得"""
        if self._memory_service is None:
            self._memory_service = ChromaDBService(self.config, self.llm_service)
        return self._memory_service

    @property
    def conversation_service(self) -> ConversationService:
        """会話サービスの取得"""
        if self._conversation_service is None:
            self._conversation_service = ConversationService(
                self.config,
                self.character_service,
                self.memory_service,
                self.llm_service
            )
        return self._conversation_service 