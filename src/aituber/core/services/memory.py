"""メモリサービスの基本定義"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from pydantic import BaseModel, Field

from ..config import AITuberConfig, MemoryConfig
from ..exceptions import MemoryError
from .llm import LLMService


class Memory(BaseModel):
    """メモリエントリ"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    character_id: str
    user_id: str
    text: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class MemoryService:
    """メモリ管理サービス"""

    def __init__(self, config: AITuberConfig, llm_service: LLMService):
        """
        メモリ管理サービスの初期化

        Args:
            config: アプリケーション設定
            llm_service: LLMサービス
        """
        self._config = config
        self.llm_service = llm_service
        self.memories: Dict[str, List[Memory]] = {}

    @property
    def config(self) -> AITuberConfig:
        """設定を取得"""
        return self._config

    async def add_memory(
        self,
        character_id: str,
        user_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Memory:
        """新しい記憶を追加"""
        try:
            # 埋め込みベクトルの生成
            embedding = await self.llm_service.get_embeddings([text])

            # メモリの作成
            memory = Memory(
                character_id=character_id,
                user_id=user_id,
                text=text,
                embedding=embedding[0] if embedding else None,
                metadata=metadata or {}
            )

            # キャラクターごとのメモリリストに追加
            if character_id not in self.memories:
                self.memories[character_id] = []
            self.memories[character_id].append(memory)

            return memory
        except Exception as e:
            raise MemoryError(f"記憶の追加中にエラーが発生しました: {e}")

    async def retrieve_relevant_memories(
        self,
        character_id: str,
        query: str,
        limit: int = 5
    ) -> List[Memory]:
        """関連する記憶を取得"""
        try:
            if character_id not in self.memories:
                return []

            # クエリの埋め込みベクトルを生成
            query_embedding = await self.llm_service.get_embeddings([query])
            if not query_embedding:
                return []

            # コサイン類似度に基づいて関連メモリを取得
            memories = self.memories[character_id]
            scored_memories = []
            for memory in memories:
                if memory.embedding:
                    similarity = self._cosine_similarity(query_embedding[0], memory.embedding)
                    scored_memories.append((similarity, memory))

            # スコアでソートし、上位N件を返す
            scored_memories.sort(reverse=True, key=lambda x: x[0])
            return [memory for _, memory in scored_memories[:limit]]

        except Exception as e:
            raise MemoryError(f"記憶の検索中にエラーが発生しました: {e}")

    def get_memories(
        self,
        character_id: str,
        limit: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> List[Memory]:
        """メモリの取得"""
        if character_id not in self.memories:
            return []

        memories = self.memories[character_id]
        if user_id:
            memories = [m for m in memories if m.user_id == user_id]

        if limit:
            memories = memories[-limit:]

        return memories

    def clear_memories(self, character_id: str, user_id: Optional[str] = None) -> None:
        """メモリのクリア"""
        if character_id not in self.memories:
            return

        if user_id:
            self.memories[character_id] = [
                m for m in self.memories[character_id]
                if m.user_id != user_id
            ]
        else:
            self.memories[character_id] = []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """コサイン類似度の計算"""
        if len(vec1) != len(vec2):
            raise ValueError("ベクトルの次元が一致しません")

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0

        return dot_product / (norm1 * norm2) 