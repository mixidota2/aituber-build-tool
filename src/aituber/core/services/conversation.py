"""Conversation management service implementation."""

from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import uuid

from pydantic import BaseModel, Field

from ..config import AITuberConfig
from ..exceptions import LLMError
from .character import CharacterService
from .memory.base import BaseMemoryService, Memory
from .llm.base import BaseLLMService, Message
from ..models.character import Character


class ConversationContext(BaseModel):
    """会話コンテキスト"""

    character_id: str
    user_id: str
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Message] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ConversationService:
    """会話管理サービス"""

    def __init__(
        self,
        config: AITuberConfig,
        character_service: CharacterService,
        memory_service: BaseMemoryService,
        llm_service: BaseLLMService,
    ):
        self.config = config
        self.character_service = character_service
        self.memory_service = memory_service
        self.llm_service = llm_service
        self.active_conversations: Dict[str, ConversationContext] = {}

    async def process_message(self, conversation_id: str, user_message: str) -> str:
        """ユーザーメッセージの処理と応答生成"""
        # 会話コンテキスト取得
        context = self.active_conversations.get(conversation_id)
        if not context:
            raise ValueError(f"会話が見つかりません: {conversation_id}")

        # キャラクター取得
        character = self.character_service.get_character(context.character_id)

        # ユーザーメッセージ追加
        user_msg = Message(role="user", content=user_message)
        context.messages.append(user_msg)

        # 関連記憶の取得
        memories = await self.memory_service.retrieve_relevant_memories(
            character.id, user_message, limit=5
        )

        # プロンプト構築
        prompt_messages = await self._build_prompt(context, character, memories)

        # LLM応答生成
        try:
            response = await self.llm_service.generate(prompt_messages)

            # 応答を会話履歴に追加
            assistant_msg = Message(role="assistant", content=response)
            context.messages.append(assistant_msg)

            # 更新時間の更新
            context.updated_at = datetime.now()

            # 新しい記憶の保存
            await self.memory_service.add_memory(
                character_id=character.id,
                user_id=context.user_id,
                text=f"User: {user_message}\nAssistant: {response}",
            )

            return response
        except Exception as e:
            raise LLMError(f"応答生成中にエラーが発生しました: {e}")

    async def process_message_stream(
        self, conversation_id: str, user_message: str
    ) -> AsyncGenerator[str, None]:
        """ユーザーメッセージの処理とストリーミング応答生成"""
        # 会話コンテキスト取得
        context = self.active_conversations.get(conversation_id)
        if not context:
            raise ValueError(f"会話が見つかりません: {conversation_id}")

        # キャラクター取得
        character = self.character_service.get_character(context.character_id)

        # ユーザーメッセージ追加
        user_msg = Message(role="user", content=user_message)
        context.messages.append(user_msg)

        # 関連記憶の取得
        memories = await self.memory_service.retrieve_relevant_memories(
            character.id, user_message, limit=5
        )

        # プロンプト構築
        prompt_messages = await self._build_prompt(context, character, memories)

        # LLM応答生成 (ストリーミング)
        try:
            full_response = ""
            stream = await self.llm_service.generate_stream(prompt_messages)
            async for token in stream:
                full_response += token
                yield token

            # 応答を会話履歴に追加
            assistant_msg = Message(role="assistant", content=full_response)
            context.messages.append(assistant_msg)

            # 更新時間の更新
            context.updated_at = datetime.now()

            # 新しい記憶の保存
            await self.memory_service.add_memory(
                character_id=character.id,
                user_id=context.user_id,
                text=f"User: {user_message}\nAssistant: {full_response}",
            )

        except Exception as e:
            raise LLMError(f"ストリーミング応答生成中にエラーが発生しました: {e}")

    async def _build_prompt(
        self,
        context: ConversationContext,
        character: Character,
        memories: List[Memory] | None = None,
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
        history_limit = 10
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

    async def summarize_conversation(self, conversation_id: str) -> str:
        """会話の要約を生成する"""
        context = self.get_conversation(conversation_id)
        if not context or len(context.messages) < 3:
            return "会話が十分ではありません。"
        conversation_text = "\n".join(
            f"{msg.role}: {msg.content}" for msg in context.messages
        )
        system_template = (
            "あなたは会話の要約を生成するアシスタントです。\n"
            "以下の会話を3-5文で要約してください。会話の主要な内容と重要な情報を含めてください。"
        )
        human_template = "{conversation}"
        summary = await self.llm_service.generate_with_template(
            system_template=system_template,
            human_template=human_template,
            variables={"conversation": conversation_text},
        )
        return summary
