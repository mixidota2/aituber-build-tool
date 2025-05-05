"""ChromaDBを使用したメモリサービスの実装"""

from typing import (
    List,
    Dict,
    Any,
    Optional,
    cast,
    TypedDict,
    Union,
    TypeVar,
    Protocol,
    runtime_checkable,
)
from typing_extensions import TypeGuard
from datetime import datetime
import uuid

import chromadb
from chromadb.config import Settings
from chromadb.api.types import Where, Metadata

from ....core.config import AITuberConfig
from ....core.exceptions import MemoryError
from .base import BaseMemoryService, Memory
from ..llm.base import BaseLLMService

T = TypeVar("T")


class MemoryMetadata(TypedDict):
    """メモリのメタデータの型定義"""

    character_id: str
    user_id: str
    created_at: str
    updated_at: str
    additional_context: Optional[Dict[str, str]]  # ChromaDBはstr型のみサポート


@runtime_checkable
class ResultProtocol(Protocol):
    def get(self, key: str, default: Any = None) -> Any: ...


def is_valid_result(obj: Any) -> TypeGuard[ResultProtocol]:
    """オブジェクトがResultProtocolを満たすかチェック"""
    return hasattr(obj, "get") and callable(obj.get)


# ChromaDBの型定義
class ChromaResult(TypedDict, total=False):
    ids: List[Union[str, List[str]]]
    documents: List[Union[str, List[str]]]
    metadatas: List[Union[Dict[str, Any], List[Dict[str, Any]]]]
    embeddings: List[Union[List[float], List[List[float]]]]
    distances: List[Union[float, List[float]]]


class ChromaDBMemoryService(BaseMemoryService):
    """ChromaDBを使用したメモリサービス"""

    def __init__(self, config: AITuberConfig, llm_service: BaseLLMService):
        """初期化

        Args:
            config: アプリケーション設定
            llm_service: LLMサービス
        """
        self.config = config
        self.llm_service = llm_service
        self.client = chromadb.PersistentClient(
            path=str(self.config.memory.vector_db_path),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=str(self.config.memory.collection_name)
        )

    def _convert_metadata_to_chroma(self, metadata: Dict[str, Any]) -> Dict[str, str]:
        """メタデータをChromaDB形式に変換"""
        if not metadata:
            return {}

        chroma_metadata: Dict[str, str] = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                chroma_metadata[key] = str(value)
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_value is not None and isinstance(
                        sub_value, (str, int, float, bool)
                    ):
                        chroma_metadata[f"{key}.{sub_key}"] = str(sub_value)
            elif isinstance(value, (list, tuple)):
                valid_items = [
                    str(item)
                    for item in value
                    if item is not None and isinstance(item, (str, int, float, bool))
                ]
                if valid_items:
                    chroma_metadata[key] = ",".join(valid_items)
        return chroma_metadata

    def _convert_chroma_to_memory(
        self,
        id: str,
        text: str,
        metadata: Metadata,
        embedding: Optional[List[float]] = None,
    ) -> Memory:
        """ChromaDBの結果をメモリオブジェクトに変換

        Args:
            id: メモリID（必須）
            text: メモリのテキスト内容（必須）
            metadata: メタデータ（必須）
            embedding: 埋め込みベクトル（オプション）

        Returns:
            Memory: 変換されたメモリオブジェクト

        Raises:
            ValueError: 必須パラメータがNoneの場合
        """
        if id is None or text is None or metadata is None:
            raise ValueError("必須パラメータがNoneです")

        return Memory(
            id=id,
            character_id=str(metadata["character_id"]),
            user_id=str(metadata["user_id"]),
            text=text,
            embedding=embedding,
            metadata={
                k: v
                for k, v in metadata.items()
                if k not in ["character_id", "user_id", "created_at", "updated_at"]
            },
            created_at=datetime.fromisoformat(str(metadata["created_at"])),
            updated_at=datetime.fromisoformat(str(metadata["updated_at"])),
        )

    def _validate_get_result(self, result: Any) -> TypeGuard[ChromaResult]:
        """GetResultの検証"""
        if not isinstance(result, dict):
            return False
        required_keys = ["ids", "documents", "metadatas"]
        if not all(key in result for key in required_keys):
            return False
        if not all(isinstance(result.get(key), list) for key in required_keys):
            return False
        if not all(result.get(key) for key in required_keys):  # 空リストのチェック
            return False
        return True

    def _validate_query_result(self, result: Any) -> TypeGuard[ChromaResult]:
        """QueryResultの検証"""
        if not isinstance(result, dict):
            return False
        required_keys = ["ids", "documents", "metadatas", "distances"]
        if not all(key in result for key in required_keys):
            return False
        if not all(isinstance(result.get(key), list) for key in required_keys):
            return False
        if not all(result.get(key) for key in required_keys):  # 空リストのチェック
            return False

        # リストの要素が正しい型かチェック
        try:
            for key in required_keys:
                value = result.get(key)
                if not isinstance(value, list) or not value:
                    return False
                if not isinstance(value[0], list):
                    return False
                if not value[0]:  # 空のサブリストをチェック
                    return False
        except (TypeError, AttributeError, IndexError):
            return False
        return True

    def _safe_get_from_result(
        self, result: Any, key: str, index: int, subindex: Optional[int] = None
    ) -> Any:
        """結果から安全に値を取得する

        Args:
            result: ChromaDBの結果オブジェクト
            key: 取得するキー
            index: 配列のインデックス
            subindex: ネストされた配列のインデックス（オプション）

        Returns:
            Any: 取得した値。エラーの場合はNone
        """
        if not isinstance(result, dict):
            return None
        try:
            value = result.get(key, [])
            if not isinstance(value, list) or not value:
                return None
            if subindex is not None:
                if not isinstance(value[0], list) or len(value[0]) <= subindex:
                    return None
                item = value[0][subindex]
            else:
                if len(value) <= index:
                    return None
                item = value[index]
            # IDの場合は文字列に変換
            if key == "ids" and isinstance(item, list):
                return item[0] if item else None
            return item
        except (IndexError, TypeError, AttributeError) as e:
            print(
                f"値の取得に失敗しました - キー: {key}, インデックス: {index}, サブインデックス: {subindex}, エラー: {e}"
            )
            return None

    def _get_embedding(
        self, result: Any, index: int, is_query: bool = False
    ) -> Optional[List[float]]:
        """埋め込みベクトルを安全に取得

        Args:
            result: ChromaDBの結果オブジェクト
            index: 配列のインデックス
            is_query: クエリ結果からの取得かどうか

        Returns:
            Optional[List[float]]: 埋め込みベクトル。エラーの場合はNone
        """
        if not isinstance(result, dict):
            return None
        try:
            embeddings = result.get("embeddings", [])
            if not isinstance(embeddings, list) or not embeddings:
                return None
            if is_query:
                if not isinstance(embeddings[0], list) or not embeddings[0]:
                    return None
                if len(embeddings[0]) <= index:
                    return None
                embedding = embeddings[0][index]
            else:
                if len(embeddings) <= index:
                    return None
                embedding = embeddings[index]
            return cast(List[float], embedding) if isinstance(embedding, list) else None
        except (IndexError, TypeError, AttributeError) as e:
            print(
                f"埋め込みベクトルの取得に失敗しました - インデックス: {index}, クエリ: {is_query}, エラー: {e}"
            )
            return None

    def _ensure_str_id(self, id_value: Union[str, List[str]]) -> Optional[str]:
        """IDを文字列に変換

        Args:
            id_value: 変換する値（文字列または文字列のリスト）

        Returns:
            Optional[str]: 変換された文字列ID。変換できない場合はNone

        Note:
            返り値がNoneの場合は、呼び出し側で適切に処理する必要があります。
        """
        if isinstance(id_value, str):
            return id_value
        if isinstance(id_value, list) and id_value and isinstance(id_value[0], str):
            return id_value[0]
        print(f"IDの文字列変換に失敗しました - 値: {id_value}")
        return None

    async def add_memory(
        self,
        character_id: str,
        user_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Memory:
        """メモリを追加する

        Args:
            character_id: キャラクターID
            user_id: ユーザーID
            text: メモリのテキスト内容
            metadata: 追加のメタデータ（オプション）

        Returns:
            Memory: 作成されたメモリオブジェクト

        Raises:
            MemoryError: メモリの追加に失敗した場合
        """
        try:
            memory_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            # メタデータの準備
            base_metadata = {
                "character_id": character_id,
                "user_id": user_id,
                "created_at": now,
                "updated_at": now,
            }
            if metadata:
                base_metadata.update(self._convert_metadata_to_chroma(metadata))

            # 埋め込みベクトルの生成
            embeddings = await self.llm_service.get_embeddings([text])
            embedding = embeddings[0]

            # ChromaDBに保存
            self.collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                metadatas=[base_metadata],
                documents=[text],
            )

            return Memory(
                id=memory_id,
                character_id=character_id,
                user_id=user_id,
                text=text,
                embedding=embedding,
                metadata=metadata or {},
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
            )
        except Exception as e:
            raise MemoryError(f"メモリの追加に失敗しました: {e}")

    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """メモリを取得する"""
        try:
            result = cast(
                ChromaResult,
                self.collection.get(
                    ids=[memory_id], include=["metadatas", "documents", "embeddings"]
                ),
            )
            if not self._validate_get_result(result):
                return None

            memory_id = self._safe_get_from_result(result, "ids", 0)
            text = self._safe_get_from_result(result, "documents", 0)
            metadata = self._safe_get_from_result(result, "metadatas", 0)

            if not all([memory_id, text, metadata]):
                return None

            return self._convert_chroma_to_memory(
                id=memory_id,
                text=text,
                metadata=cast(Metadata, metadata),
                embedding=self._get_embedding(result, 0),
            )
        except Exception as e:
            print(f"メモリの取得に失敗しました: {e}")
            return None

    async def get_memories(
        self,
        character_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Memory]:
        """メモリ一覧を取得する"""
        where: Where = {"character_id": {"$eq": character_id}}
        try:
            result = cast(
                ChromaResult,
                self.collection.get(
                    where=where,
                    limit=limit,
                    offset=offset,
                    include=["metadatas", "documents", "embeddings"],
                ),
            )

            if not self._validate_get_result(result):
                return []

            memories = []
            for i, memory_id in enumerate(result.get("ids", [])):
                text = self._safe_get_from_result(result, "documents", i)
                metadata = self._safe_get_from_result(result, "metadatas", i)
                str_memory_id = self._ensure_str_id(memory_id)

                if str_memory_id is None or text is None or metadata is None:
                    continue

                # 型チェックの保証
                assert isinstance(str_memory_id, str), (
                    "str_memory_idはstr型である必要があります"
                )
                assert isinstance(text, str), "textはstr型である必要があります"
                assert isinstance(metadata, dict), (
                    "metadataはdict型である必要があります"
                )

                try:
                    memory = self._convert_chroma_to_memory(
                        id=str_memory_id,
                        text=text,
                        metadata=cast(Metadata, metadata),
                        embedding=self._get_embedding(result, i),
                    )
                    memories.append(memory)
                except ValueError as e:
                    print(
                        f"メモリの変換に失敗しました - ID: {str_memory_id}, エラー: {e}"
                    )
                    continue

            return memories
        except Exception as e:
            print(f"メモリ一覧の取得に失敗しました: {e}")
            return []

    async def retrieve_relevant_memories(
        self, character_id: str, query: str, limit: int = 5, threshold: float = 0.7
    ) -> List[Memory]:
        """関連するメモリを検索する"""
        try:
            # クエリの埋め込みベクトルを生成
            embeddings = await self.llm_service.get_embeddings([query])
            embedding = embeddings[0]

            # ChromaDBで類似度検索
            where: Where = {"character_id": {"$eq": character_id}}
            result = cast(
                ChromaResult,
                self.collection.query(
                    query_embeddings=[embedding],
                    where=where,
                    n_results=limit,
                    include=["metadatas", "documents", "embeddings", "distances"],
                ),
            )

            if not self._validate_query_result(result):
                return []

            # 類似度に基づいてフィルタリング
            memories = []
            ids = result.get("ids", [[]])[0]
            for i, memory_id in enumerate(ids):
                distance = self._safe_get_from_result(result, "distances", 0, i)
                if distance is None:
                    continue

                # ChromaDBの距離を類似度に変換（1 - 距離）
                similarity = 1 - distance
                if similarity >= threshold:
                    text = self._safe_get_from_result(result, "documents", 0, i)
                    metadata = self._safe_get_from_result(result, "metadatas", 0, i)
                    str_memory_id = self._ensure_str_id(memory_id)

                    if str_memory_id is None or text is None or metadata is None:
                        continue

                    # 型チェックの保証
                    assert isinstance(str_memory_id, str), (
                        "str_memory_idはstr型である必要があります"
                    )
                    assert isinstance(text, str), "textはstr型である必要があります"
                    assert isinstance(metadata, dict), (
                        "metadataはdict型である必要があります"
                    )

                    try:
                        memory = self._convert_chroma_to_memory(
                            id=str_memory_id,
                            text=text,
                            metadata=cast(Metadata, metadata),
                            embedding=self._get_embedding(result, i, is_query=True),
                        )
                        memories.append(memory)
                    except ValueError as e:
                        print(
                            f"メモリの変換に失敗しました - ID: {str_memory_id}, エラー: {e}"
                        )
                        continue

            return memories

        except Exception as e:
            print(f"関連メモリの検索に失敗しました: {e}")
            return []

    async def update_memory(
        self,
        memory_id: str,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Memory:
        """メモリを更新する"""
        try:
            # 既存のメモリを取得
            existing = await self.get_memory(memory_id)
            if not existing:
                raise MemoryError(f"メモリが見つかりません: {memory_id}")

            # 更新するデータの準備
            update_metadata = existing.metadata.copy()
            if metadata:
                update_metadata.update(metadata)

            # ChromaDBのメタデータ形式に変換
            chroma_metadata = self._convert_metadata_to_chroma(
                {
                    "character_id": existing.character_id,
                    "user_id": existing.user_id,
                    "created_at": existing.created_at.isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    **update_metadata,
                }
            )

            # テキストが更新される場合は新しい埋め込みベクトルを生成
            update_text = text if text is not None else existing.text
            if text is not None:
                embeddings = await self.llm_service.get_embeddings([update_text])
                embedding = embeddings[0]
            else:
                embedding = existing.embedding

            # ChromaDBのデータを更新
            self.collection.update(
                ids=[memory_id],
                embeddings=[embedding] if embedding else None,
                metadatas=[chroma_metadata],
                documents=[update_text],
            )

            return Memory(
                id=memory_id,
                character_id=existing.character_id,
                user_id=existing.user_id,
                text=update_text,
                embedding=embedding,
                metadata=update_metadata,
                created_at=existing.created_at,
                updated_at=datetime.now(),
            )

        except Exception as e:
            raise MemoryError(f"メモリの更新に失敗しました: {e}")

    async def delete_memory(self, memory_id: str) -> bool:
        """メモリを削除する"""
        try:
            # メモリの存在確認
            existing = await self.get_memory(memory_id)
            if not existing:
                return False

            # ChromaDBから削除
            self.collection.delete(ids=[memory_id])
            return True

        except Exception as e:
            print(f"メモリの削除に失敗しました: {e}")
            return False
