"""Memory management for AITuber framework."""

from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from langchain_community.vectorstores import Chroma

from .models import Memory, MemoryType
from ..core.context import AppContext
from ..core.events import EventType
from ..core.exceptions import MemoryError
from ..llm.langchain_integration import LangChainService


class MemoryManager:
    """記憶の管理"""

    def __init__(self, app_context: AppContext):
        self.app_context = app_context
        self.langchain_service: LangChainService = self.app_context.get_service(
            "langchain_service"
        )

        # ベクトルDBのディレクトリ作成
        vector_db_path = self.app_context.config.memory.vector_db_path
        os.makedirs(vector_db_path, exist_ok=True)

        # LangChain Chroma DBの初期化
        embeddings = self.langchain_service.embeddings
        self.vector_store = Chroma(
            persist_directory=vector_db_path, embedding_function=embeddings
        )

        # メモリキャッシュ
        self.memory_cache: Dict[str, Memory] = {}

    async def add_memory(
        self,
        character_id: str,
        user_id: str,
        text: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Memory:
        """記憶の追加"""
        try:
            meta = metadata or {}
            meta.update(
                {
                    "character_id": character_id,
                    "user_id": user_id,
                    "memory_type": memory_type,
                    "importance": importance,
                    "created_at": datetime.now().isoformat(),
                }
            )

            # メモリオブジェクト作成
            memory = Memory(
                character_id=character_id,
                user_id=user_id,
                text=text,
                memory_type=memory_type,
                importance=importance,
                metadata=meta,
            )

            # ベクトルDBへの保存
            ids = self.vector_store.add_texts(
                texts=[text], metadatas=[meta], ids=[memory.id]
            )

            # 埋め込みIDを設定
            memory.embedding_id = ids[0]

            # キャッシュに追加
            self.memory_cache[memory.id] = memory

            # イベント発行
            self.app_context.publish_event(
                EventType.MEMORY_ADDED,
                data={"memory_id": memory.id, "character_id": character_id},
                source="memory_manager",
            )

            return memory
        except Exception as e:
            raise MemoryError(f"記憶の追加中にエラーが発生しました: {e}")

    async def retrieve_relevant_memories(
        self, character_id: str, query: str, limit: int = 5
    ) -> List[Memory]:
        """関連する記憶の取得"""
        try:
            # 類似記憶検索
            filter_metadata = {"character_id": character_id}
            docs_and_scores = self.vector_store.similarity_search_with_score(
                query=query, k=limit, filter=filter_metadata
            )

            # Memory オブジェクトへの変換
            memories = []
            for doc, score in docs_and_scores:
                meta = doc.metadata
                doc_id = doc.id

                # IDがない場合はスキップ
                if doc_id is None:
                    continue

                # キャッシュにあれば利用
                if doc_id in self.memory_cache:
                    memory = self.memory_cache[doc_id]
                    # アクセス情報更新
                    memory.last_accessed = datetime.now()
                    memory.access_count += 1
                else:
                    # メタデータから必須値を取得（デフォルト値を設定）
                    char_id = meta.get("character_id")
                    if char_id is None:
                        char_id = character_id  # フィルタで指定したものを使用

                    # 新しくMemoryオブジェクトを作成
                    memory = Memory(
                        id=doc_id,
                        character_id=char_id,
                        user_id=meta.get("user_id", "unknown"),
                        text=doc.page_content,
                        memory_type=meta.get("memory_type", MemoryType.SHORT_TERM),
                        importance=meta.get("importance", 0.5),
                        embedding_id=doc_id,
                        last_accessed=datetime.now(),
                        access_count=1,
                        metadata=meta,
                    )
                    # キャッシュに追加
                    self.memory_cache[doc_id] = memory

                memories.append(memory)

            # イベント発行
            if memories:
                self.app_context.publish_event(
                    EventType.MEMORY_RETRIEVED,
                    data={
                        "character_id": character_id,
                        "query": query,
                        "memory_count": len(memories),
                    },
                    source="memory_manager",
                )

            return memories
        except Exception as e:
            raise MemoryError(f"記憶の検索中にエラーが発生しました: {e}")

    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """指定IDの記憶を取得"""
        # キャッシュにあれば返す
        if memory_id in self.memory_cache:
            return self.memory_cache[memory_id]

        try:
            # ベクトルDBから検索
            docs = self.vector_store.get([memory_id])
            if docs and docs["documents"]:
                doc = docs["documents"][0]
                meta = docs["metadatas"][0]

                memory = Memory(
                    id=memory_id,
                    character_id=meta.get("character_id", "unknown"),
                    user_id=meta.get("user_id", "unknown"),
                    text=doc,
                    memory_type=meta.get("memory_type", MemoryType.SHORT_TERM),
                    importance=meta.get("importance", 0.5),
                    embedding_id=memory_id,
                    metadata=meta,
                )

                # キャッシュに追加
                self.memory_cache[memory_id] = memory
                return memory

            return None
        except Exception as e:
            raise MemoryError(f"記憶の取得中にエラーが発生しました: {e}")

    async def update_memory(
        self, memory_id: str, updates: Dict[str, Any]
    ) -> Optional[Memory]:
        """記憶の更新"""
        memory = await self.get_memory(memory_id)
        if not memory:
            return None

        try:
            # メモリオブジェクトの更新
            for key, value in updates.items():
                if hasattr(memory, key):
                    setattr(memory, key, value)

            # ベクトルDBのメタデータ更新
            meta = memory.metadata.copy()
            for key, value in updates.items():
                if key in meta:
                    meta[key] = value

            # テキストが更新された場合は埋め込みも更新
            if "text" in updates:
                # 古いエントリ削除
                self.vector_store.delete([memory_id])

                # 新しい埋め込み取得
                embeddings = await self.langchain_service.get_embeddings([memory.text])

                # 再登録
                self.vector_store.add_texts(
                    texts=[memory.text],
                    metadatas=[meta],
                    ids=[memory_id],
                    embeddings=embeddings,
                )
            else:
                # メタデータのみ更新
                # Note: Chromaはメタデータのみの更新をサポートしていないため、
                # 削除して再追加が必要（ここでは簡略化）
                pass

            # キャッシュ更新
            self.memory_cache[memory_id] = memory

            return memory
        except Exception as e:
            raise MemoryError(f"記憶の更新中にエラーが発生しました: {e}")

    async def delete_memory(self, memory_id: str) -> None:
        """記憶の削除"""
        try:
            # ベクトルDBから削除
            self.vector_store.delete([memory_id])

            # キャッシュから削除
            if memory_id in self.memory_cache:
                del self.memory_cache[memory_id]
        except Exception as e:
            raise MemoryError(f"記憶の削除中にエラーが発生しました: {e}")

    async def summarize_conversation(self, conversation_id: str) -> str:
        """会話の要約"""
        try:
            # 会話マネージャーから会話履歴取得
            conversation_manager = self.app_context.get_service("conversation_manager")
            context = conversation_manager.get_conversation(conversation_id)

            if not context or len(context.messages) < 3:
                return "会話が十分ではありません。"

            # 会話内容
            conversation_text = "\n".join(
                [f"{msg.role}: {msg.content}" for msg in context.messages]
            )

            # 要約プロンプト
            system_template = """
あなたは会話の要約を生成するアシスタントです。
以下の会話を3-5文で要約してください。会話の主要な内容と重要な情報を含めてください。
"""

            human_template = "{conversation}"

            # LangChainで要約生成
            summary = await self.langchain_service.generate_with_template(
                system_template=system_template,
                human_template=human_template,
                variables={"conversation": conversation_text},
            )

            return summary
        except Exception as e:
            raise MemoryError(f"会話の要約中にエラーが発生しました: {e}")
