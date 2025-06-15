"""会話管理機能のテスト."""

import pytest
from unittest.mock import MagicMock, AsyncMock, create_autospec
from aituber.core.services.conversation import ConversationService, ConversationContext
from aituber.core.services.llm.base import Message
from aituber.core.container import ServiceContainer
from aituber.core.services.character import CharacterService
from aituber.core.services.llm.base import BaseLLMService
from aituber.core.services.memory.base import BaseMemoryService
from aituber.core.models.character import Character, Persona


@pytest.fixture
def sample_character():
    """サンプルキャラクターのフィクスチャ."""
    return Character(
        id="test_char",
        name="テストキャラクター",
        description="テスト用のキャラクター",
        system_prompt="あなたはテストキャラクターです。",
        persona=Persona(
            age=20,
            gender="female",
            occupation="学生",
            background="テスト大学に通う大学生",
            appearance="長い黒髪、制服姿",
            speech_style="丁寧な口調"
        )
    )


@pytest.fixture
def container() -> ServiceContainer:
    """DIコンテナのフィクスチャ."""
    container = ServiceContainer(config=MagicMock())
    
    # 各サービスのモックを作成
    llm_mock = MagicMock(spec=BaseLLMService)
    character_mock = MagicMock(spec=CharacterService)
    memory_mock = create_autospec(BaseMemoryService, instance=True)
    
    # モックをコンテナに設定
    container._llm_service = llm_mock
    container._character_service = character_mock
    container._memory_service = memory_mock
    
    return container


@pytest.fixture
def conversation_service(container: ServiceContainer) -> ConversationService:
    """会話サービスのフィクスチャ."""
    return container.conversation_service


def test_get_or_create_conversation(
    conversation_service: ConversationService,
    sample_character: Character,
    container: ServiceContainer,
) -> None:
    """会話作成のテスト."""
    character_service = container.character_service
    character_service.get_character.return_value = sample_character
    
    ctx = conversation_service.get_or_create_conversation(
        character_id=sample_character.id,
        user_id="test_user"
    )
    
    assert isinstance(ctx, ConversationContext)
    assert ctx.character_id == sample_character.id
    assert ctx.user_id == "test_user"
    
    # 同じIDで取得した場合は同じインスタンスが返される
    ctx2 = conversation_service.get_or_create_conversation(
        character_id=sample_character.id,
        user_id="test_user",
        conversation_id=ctx.conversation_id
    )
    assert ctx is ctx2


def test_delete_conversation(
    conversation_service: ConversationService,
    sample_character: Character,
    container: ServiceContainer,
) -> None:
    """会話削除のテスト."""
    character_service = container.character_service
    character_service.get_character.return_value = sample_character
    
    ctx = conversation_service.get_or_create_conversation(
        character_id=sample_character.id,
        user_id="test_user"
    )
    
    conversation_service.delete_conversation(ctx.conversation_id)
    assert conversation_service.get_conversation(ctx.conversation_id) is None


@pytest.mark.asyncio
async def test_process_message(
    conversation_service: ConversationService,
    container: ServiceContainer,
    sample_character: Character,
) -> None:
    """メッセージ処理のテスト."""
    character_service = container.character_service
    character_service.get_character.return_value = sample_character
    llm_service = container.llm_service
    llm_service.generate = AsyncMock(return_value="AI応答")
    
    ctx = conversation_service.get_or_create_conversation(
        character_id=sample_character.id,
        user_id="test_user"
    )
    
    response = await conversation_service.process_message(
        conversation_id=ctx.conversation_id,
        user_message="こんにちは"
    )
    
    assert response == "AI応答"
    assert len(ctx.messages) == 2  # ユーザーメッセージとAI応答
    assert ctx.messages[-1].content == "AI応答"
    assert ctx.messages[-1].role == "assistant"


@pytest.mark.asyncio
async def test_process_message_stream(
    conversation_service: ConversationService,
    container: ServiceContainer,
    sample_character: Character,
) -> None:
    """ストリーミングメッセージ処理のテスト."""
    character_service = container.character_service
    character_service.get_character.return_value = sample_character
    llm_service = container.llm_service

    tokens = ["A", "I", "応", "答"]

    class AsyncIteratorMock:
        def __init__(self, tokens):
            self.tokens = tokens
            self.index = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.index >= len(self.tokens):
                raise StopAsyncIteration
            token = self.tokens[self.index]
            self.index += 1
            return token

    mock_generator = AsyncIteratorMock(tokens)
    llm_service.generate_stream = AsyncMock(return_value=mock_generator)

    ctx = conversation_service.get_or_create_conversation(
        character_id=sample_character.id,
        user_id="test_user"
    )

    received_tokens = []
    async for token in conversation_service.process_message_stream(
        conversation_id=ctx.conversation_id,
        user_message="こんにちは"
    ):
        received_tokens.append(token)

    assert received_tokens == tokens
    assert len(ctx.messages) == 2
    assert ctx.messages[-1].content == "AI応答"
    assert ctx.messages[-1].role == "assistant"


@pytest.mark.asyncio
async def test_summarize_conversation(
    conversation_service: ConversationService,
    container: ServiceContainer,
    sample_character: Character,
) -> None:
    """会話要約のテスト."""
    character_service = container.character_service
    character_service.get_character.return_value = sample_character
    llm_service = container.llm_service
    llm_service.generate_with_template = AsyncMock(return_value="要約結果")
    
    ctx = conversation_service.get_or_create_conversation(
        character_id=sample_character.id,
        user_id="test_user"
    )
    
    # 会話履歴の追加
    ctx.messages.append(Message(role="user", content="こんにちは"))
    ctx.messages.append(Message(role="assistant", content="やあ"))
    ctx.messages.append(Message(role="user", content="元気？"))
    
    summary = await conversation_service.summarize_conversation(ctx.conversation_id)
    assert summary == "要約結果" 