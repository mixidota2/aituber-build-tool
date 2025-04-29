"""ChromaDBを使用したメモリサービスの実装"""

from typing import List, Dict, Any, Optional, cast, Sequence, TypedDict, Union
from datetime import datetime
import uuid

from pydantic import BaseModel, Field
import chromadb
from chromadb.config import Settings
from chromadb.api.types import QueryResult, Document, GetResult, Include, Where, WhereDocument, Metadata

from ...core.config import AITuberConfig, MemoryConfig
from ...core.services.memory import MemoryService, Memory
from ...core.services.llm import LLMService
from ...core.exceptions import MemoryError


class MemoryMetadata(TypedDict):
    """メモリのメタデータの型定義"""
    timestamp: str
    character_id: str
    source: str
    additional_context: Optional[Dict[str, str]]  # ChromaDBはstr型のみサポート


class MemorySearchResult(TypedDict):
    """メモリ検索結果の型定義"""
    text: str
    metadata: MemoryMetadata
    similarity: float


class ChromaDBService(MemoryService):
    """ChromaDBを使用したメモリサービス"""

    def __init__(self, config: AITuberConfig, llm_service: LLMService):
        """初期化

        Args:
            config: 設定
            llm_service: LLMサービス
        """
        super().__init__(config, llm_service)
        self.client = chromadb.PersistentClient(
            path=str(self.config.memory.vector_db_path),
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        self.collection = self.client.get_or_create_collection(
            name=str(self.config.memory.collection_name)
        )

    def _convert_metadata_to_chroma(self, metadata: MemoryMetadata) -> Dict[str, Union[str, float, int, bool]]:
        """メタデータをChromaDB形式に変換"""
        chroma_metadata: Dict[str, Union[str, float, int, bool]] = {
            "timestamp": metadata["timestamp"],
            "character_id": metadata["character_id"],
            "source": metadata["source"]
        }
        additional_context = metadata.get("additional_context")
        if additional_context is not None:
            for key, value in additional_context.items():
                chroma_metadata[f"context_{key}"] = str(value)
        return chroma_metadata

    def _convert_chroma_to_metadata(self, chroma_metadata: Dict[str, Union[str, float, int, bool]]) -> MemoryMetadata:
        """ChromaDB形式のメタデータをMemoryMetadata形式に変換"""
        metadata: MemoryMetadata = {
            "timestamp": str(chroma_metadata["timestamp"]),
            "character_id": str(chroma_metadata["character_id"]),
            "source": str(chroma_metadata["source"]),
            "additional_context": {}
        }
        # context_プレフィックスのキーを追加コンテキストとして処理
        for key, value in chroma_metadata.items():
            if key.startswith("context_"):
                if metadata["additional_context"] is None:
                    metadata["additional_context"] = {}
                metadata["additional_context"][key[8:]] = str(value)
        return metadata

    async def add_memory(
        self,
        character_id: str,
        user_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Memory:
        """メモリを追加"""
        try:
            # タイムスタンプの設定
            timestamp = datetime.now()
            
            # メタデータの作成
            memory_metadata: MemoryMetadata = {
                "timestamp": timestamp.isoformat(),
                "character_id": character_id,
                "source": "conversation",
                "additional_context": {
                    "user_id": user_id,
                    **(metadata or {})
                }
            }

            # メタデータの変換
            chroma_metadata = self._convert_metadata_to_chroma(memory_metadata)

            # メモリの追加
            self.collection.add(
                documents=[text],
                metadatas=[chroma_metadata],
                ids=[timestamp.isoformat()]
            )

            # Memoryオブジェクトの作成と返却
            return Memory(
                character_id=character_id,
                user_id=user_id,
                text=text,
                metadata=metadata or {}
            )
        except Exception as e:
            raise MemoryError(f"メモリの追加に失敗しました: {str(e)}") from e

    async def search_similar(
        self,
        query: str,
        n_results: int = 5,
        character_id: Optional[str] = None
    ) -> List[MemorySearchResult]:
        """類似したメモリを検索"""
        try:
            # 検索条件の設定
            where: Optional[Where] = {"character_id": character_id} if character_id else None

            # 検索の実行
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            if not results["documents"] or not results["metadatas"] or not results["distances"]:
                return []

            # 結果の整形
            documents = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]

            return [
                {
                    "text": str(doc),
                    "metadata": self._convert_chroma_to_metadata(cast(Dict[str, Union[str, float, int, bool]], meta)),
                    "similarity": float(1.0 - dist)
                }
                for doc, meta, dist in zip(documents, metadatas, distances)
            ]
        except Exception as e:
            raise MemoryError(f"メモリの検索に失敗しました: {str(e)}") from e

    async def get_all_memories(
        self,
        character_id: Optional[str] = None
    ) -> List[MemorySearchResult]:
        """全てのメモリを取得"""
        try:
            # 検索条件の設定
            where: Optional[Where] = {"character_id": character_id} if character_id else None

            # メモリの取得
            results = self.collection.get(
                where=where,
                include=["documents", "metadatas"]
            )

            if not results["documents"] or not results["metadatas"]:
                return []

            # 結果の整形
            documents = results["documents"]
            metadatas = results["metadatas"]

            return [
                {
                    "text": str(doc),
                    "metadata": self._convert_chroma_to_metadata(cast(Dict[str, Union[str, float, int, bool]], meta)),
                    "similarity": 1.0
                }
                for doc, meta in zip(documents, metadatas)
            ]
        except Exception as e:
            raise MemoryError(f"メモリの取得に失敗しました: {str(e)}") from e

    async def get_recent(
        self,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """最近のメモリを取得"""
        try:
            # 全件取得して時系列でソート
            results = self.collection.get(
                include=["documents", "metadatas"]
            )

            if not results["documents"] or not results["metadatas"]:
                return []

            # メモリの整形
            memories = [
                {
                    "text": str(doc),
                    "metadata": self._convert_chroma_to_metadata(cast(Dict[str, Union[str, float, int, bool]], meta))
                }
                for doc, meta in zip(results["documents"], results["metadatas"])
            ]

            # タイムスタンプでソートして最新のものを返す
            memories.sort(
                key=lambda x: x["metadata"]["timestamp"],
                reverse=True
            )
            return memories[:limit]

        except Exception as e:
            raise MemoryError(f"メモリの取得に失敗しました: {str(e)}") from e

    async def clear(self) -> None:
        """メモリをクリア"""
        try:
            collection_name = str(self.config.memory.collection_name)
            self.client.delete_collection(name=collection_name)
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            raise MemoryError(f"メモリのクリア中にエラーが発生しました: {e}") 