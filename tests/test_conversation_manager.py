"""会話管理機能のテスト."""

import pytest
from unittest.mock import MagicMock, AsyncMock, create_autospec
from aituber.core.services.conversation import ConversationService, ConversationContext, Message
from aituber.core.container import Container
from aituber.core.services.character import CharacterService
from aituber.core.services.llm import LLMService
from aituber.core.services.memory import MemoryService
from typing import AsyncGenerator


@pytest.fixture
def container() -> Container:
    """DIコンテナのフィクスチャ."""
    container = Container(config=MagicMock())
    
    # 各サービスのモックを作成
    llm_mock = MagicMock(spec=LLMService)
    character_mock = MagicMock(spec=CharacterService)
    memory_mock = create_autospec(MemoryService, instance=True)
    
    # モックをコンテナに設定
    container._llm_service = llm_mock
    container._character_service = character_mock
    container._memory_service = memory_mock
    
    return container


@pytest.fixture
def sample_character() -> MagicMock:
    """サンプルキャラクターのフィクスチャ."""
    character = MagicMock()
    character.id = "test_character"
    character.name = "テストキャラクター"
    character.description = "テスト用のキャラクター"
    character.system_prompt = "あなたはテスト用のキャラクターです。"
    character.persona = MagicMock()
    character.personality_traits = []
    character.interests = []
    return character


@pytest.fixture
def conversation_service(container: Container) -> ConversationService:
    """会話サービスのフィクスチャ."""
    return container.conversation_service


def test_get_or_create_conversation(
    conversation_service: ConversationService,
    sample_character: MagicMock,
    container: Container,
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
    sample_character: MagicMock,
    container: Container,
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
    container: Container,
    sample_character: MagicMock,
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
    container: Container,
    sample_character: MagicMock,
) -> None:
    """ストリーミングメッセージ処理のテスト."""
    character_service = container.character_service
    character_service.get_character.return_value = sample_character
    llm_service = container.llm_service

    tokens = ["A", "I", "応", "答"]
    token_iter = iter(tokens)

    async def mock_anext(self):
        try:
            return next(token_iter)
        except StopIteration:
            raise StopAsyncIteration

    mock_generator = MagicMock()
    mock_generator.__aiter__ = MagicMock(return_value=mock_generator)
    mock_generator.__anext__ = mock_anext

    llm_service.generate_stream = MagicMock(return_value=mock_generator)

    ctx = conversation_service.get_or_create_conversation(
        character_id=sample_character.id,
        user_id="test_user"
    )

    tokens = []
    async for token in conversation_service.process_message_stream(
        conversation_id=ctx.conversation_id,
        user_message="こんにちは"
    ):
        tokens.append(token)

    assert "".join(tokens) == "AI応答"
    assert len(ctx.messages) == 2
    assert ctx.messages[-1].content == "AI応答"
    assert ctx.messages[-1].role == "assistant"


@pytest.mark.asyncio
async def test_summarize_conversation(
    conversation_service: ConversationService,
    container: Container,
    sample_character: MagicMock,
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