"""メモリサービスの基底クラス定義"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Memory(BaseModel):
    """メモリモデル"""

    id: str
    character_id: str
    user_id: str
    text: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class BaseMemoryService(ABC):
    """メモリサービスの基底クラス"""

    @abstractmethod
    async def add_memory(
        self,
        character_id: str,
        user_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Memory:
        """メモリを追加する"""
        pass

    @abstractmethod
    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """メモリを取得する"""
        pass

    @abstractmethod
    async def get_memories(
        self,
        character_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Memory]:
        """メモリ一覧を取得する"""
        pass

    @abstractmethod
    async def retrieve_relevant_memories(
        self, character_id: str, query: str, limit: int = 5, threshold: float = 0.7
    ) -> List[Memory]:
        """関連するメモリを検索する"""
        pass

    @abstractmethod
    async def update_memory(
        self,
        memory_id: str,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Memory:
        """メモリを更新する"""
        pass

    @abstractmethod
    async def delete_memory(self, memory_id: str) -> bool:
        """メモリを削除する"""
        pass
