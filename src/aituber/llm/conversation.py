"""Conversation management for AITuber framework."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from .langchain_integration import LangChainService, Message
from ..core.context import AppContext
from ..core.events import EventType
from ..core.exceptions import LLMError


class ConversationContext(BaseModel):
    """会話コンテキスト"""

    character_id: str
    user_id: str
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Message] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ConversationManager:
    """会話の管理"""

    def __init__(self, app_context: AppContext):
        self.app_context = app_context
        self.langchain_service: LangChainService = self.app_context.get_service(
            "langchain_service"
        )
        self.active_conversations: Dict[str, ConversationContext] = {}

    async def process_message(self, conversation_id: str, user_message: str) -> str:
        """ユーザーメッセージの処理と応答生成"""
        # 会話コンテキスト取得
        context = self.active_conversations.get(conversation_id)
        if not context:
            raise ValueError(f"会話が見つかりません: {conversation_id}")

        # キャラクター取得
        character_manager = self.app_context.get_service("character_manager")
        character = character_manager.load_character(context.character_id)

        # イベント発行: メッセージ受信
        self.app_context.publish_event(
            EventType.MESSAGE_RECEIVED,
            data={
                "conversation_id": conversation_id,
                "user_id": context.user_id,
                "character_id": context.character_id,
                "message": user_message,
            },
            source="conversation_manager",
        )

        # ユーザーメッセージ追加
        user_msg = Message(role="user", content=user_message)
        context.messages.append(user_msg)

        # 関連記憶の取得
        memory_manager = None
        memories = []
        if self.app_context.has_service("memory_manager"):
            memory_manager = self.app_context.get_service("memory_manager")
            memories = await memory_manager.retrieve_relevant_memories(
                character.id, user_message, limit=5
            )

        # プロンプト構築
        prompt_messages = await self._build_prompt(context, character, memories)

        # イベント発行: メッセージ処理完了
        self.app_context.publish_event(
            EventType.MESSAGE_PROCESSED,
            data={
                "conversation_id": conversation_id,
                "user_id": context.user_id,
                "character_id": context.character_id,
                "message": user_message,
            },
            source="conversation_manager",
        )

        # LLM応答生成
        try:
            response = await self.langchain_service.generate(prompt_messages)

            # 応答を会話履歴に追加
            assistant_msg = Message(role="assistant", content=response)
            context.messages.append(assistant_msg)

            # 更新時間の更新
            context.updated_at = datetime.now()

            # イベント発行: 応答生成
            self.app_context.publish_event(
                EventType.RESPONSE_GENERATED,
                data={
                    "conversation_id": conversation_id,
                    "user_id": context.user_id,
                    "character_id": context.character_id,
                    "message": response,
                },
                source="conversation_manager",
            )

            # 新しい記憶の保存
            if memory_manager:
                await memory_manager.add_memory(
                    character_id=character.id,
                    user_id=context.user_id,
                    text=f"User: {user_message}\nAssistant: {response}",
                )

            return response
        except Exception as e:
            raise LLMError(f"応答生成中にエラーが発生しました: {e}")

    async def process_message_stream(
        self, conversation_id: str, user_message: str
    ) -> Any:
        """ユーザーメッセージの処理とストリーミング応答生成"""
        # 会話コンテキスト取得
        context = self.active_conversations.get(conversation_id)
        if not context:
            raise ValueError(f"会話が見つかりません: {conversation_id}")

        # キャラクター取得
        character_manager = self.app_context.get_service("character_manager")
        character = character_manager.load_character(context.character_id)

        # イベント発行: メッセージ受信
        self.app_context.publish_event(
            EventType.MESSAGE_RECEIVED,
            data={
                "conversation_id": conversation_id,
                "user_id": context.user_id,
                "character_id": context.character_id,
                "message": user_message,
            },
            source="conversation_manager",
        )

        # ユーザーメッセージ追加
        user_msg = Message(role="user", content=user_message)
        context.messages.append(user_msg)

        # 関連記憶の取得
        memory_manager = None
        memories = []
        if self.app_context.has_service("memory_manager"):
            memory_manager = self.app_context.get_service("memory_manager")
            memories = await memory_manager.retrieve_relevant_memories(
                character.id, user_message, limit=5
            )

        # プロンプト構築
        prompt_messages = await self._build_prompt(context, character, memories)

        # イベント発行: メッセージ処理完了
        self.app_context.publish_event(
            EventType.MESSAGE_PROCESSED,
            data={
                "conversation_id": conversation_id,
                "user_id": context.user_id,
                "character_id": context.character_id,
                "message": user_message,
            },
            source="conversation_manager",
        )

        # LLM応答生成 (ストリーミング)
        try:
            full_response = ""
            async for token in self.langchain_service.generate_stream(prompt_messages):
                full_response += token
                yield token

            # 応答を会話履歴に追加
            assistant_msg = Message(role="assistant", content=full_response)
            context.messages.append(assistant_msg)

            # 更新時間の更新
            context.updated_at = datetime.now()

            # イベント発行: 応答生成
            self.app_context.publish_event(
                EventType.RESPONSE_GENERATED,
                data={
                    "conversation_id": conversation_id,
                    "user_id": context.user_id,
                    "character_id": context.character_id,
                    "message": full_response,
                },
                source="conversation_manager",
            )

            # 新しい記憶の保存
            if memory_manager:
                await memory_manager.add_memory(
                    character_id=character.id,
                    user_id=context.user_id,
                    text=f"User: {user_message}\nAssistant: {full_response}",
                )

        except Exception as e:
            raise LLMError(f"ストリーミング応答生成中にエラーが発生しました: {e}")

    async def _build_prompt(
        self, context: ConversationContext, character: Any, memories: List[Any] = None
    ) -> List[Message]:
        """プロンプトの構築（システムプロンプト、記憶、会話履歴）"""
        # システムプロンプト
        system_prompt = character.system_prompt

        # 記憶の追加
        memory_text = ""
        if memories and len(memories) > 0:
            memory_text = "以下はあなたの記憶です:\n"
            for i, memory in enumerate(memories, 1):
                memory_text += f"{i}. {memory.text}\n"

        # キャラクター情報の追加
        persona_text = f"""
あなたの名前は{character.name}です。
{character.description}

ペルソナ:
- 年齢: {character.persona.age if character.persona.age else "不明"}
- 性別: {character.persona.gender if character.persona.gender else "不明"}
- 職業: {character.persona.occupation if character.persona.occupation else "不明"}
- 背景: {character.persona.background if character.persona.background else "特になし"}
- 見た目: {character.persona.appearance if character.persona.appearance else "特になし"}
- 話し方: {character.persona.speech_style if character.persona.speech_style else "特になし"}

性格:
"""

        for trait in character.personality_traits:
            persona_text += f"- {trait.name}: {trait.description}\n"

        persona_text += "\n興味・関心:\n"
        for interest in character.interests:
            persona_text += f"- {interest.name}: {interest.description}\n"

        # 最終的なシステムプロンプト
        enhanced_system_prompt = f"{system_prompt}\n\n{persona_text}\n\n{memory_text}"

        # メッセージリスト作成
        messages = [Message(role="system", content=enhanced_system_prompt)]

        # 会話履歴の追加（最新の数件）
        history_limit = 10  # 履歴の制限数
        history = (
            context.messages[-history_limit:]
            if len(context.messages) > history_limit
            else context.messages
        )
        messages.extend(history)

        return messages

    def get_or_create_conversation(
        self, character_id: str, user_id: str, conversation_id: Optional[str] = None
    ) -> ConversationContext:
        """会話コンテキストの取得または新規作成"""
        if conversation_id and conversation_id in self.active_conversations:
            return self.active_conversations[conversation_id]

        # 新規会話作成
        context = ConversationContext(
            character_id=character_id,
            user_id=user_id,
            conversation_id=conversation_id or str(uuid.uuid4()),
        )

        self.active_conversations[context.conversation_id] = context
        return context

    def get_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
        """会話コンテキストの取得"""
        return self.active_conversations.get(conversation_id)

    def delete_conversation(self, conversation_id: str) -> None:
        """会話コンテキストの削除"""
        if conversation_id in self.active_conversations:
            del self.active_conversations[conversation_id]
