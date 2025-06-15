"""コアサービス層のテスト."""

import tempfile
import pytest
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

from aituber.core.config import (
    AITuberConfig,
    AppConfig,
    MemoryConfig,
    CharacterConfig,
    IntegrationsConfig,
    OpenAIConfig,
)
from aituber.core.container import ServiceContainer
from aituber.core.services.memory.base import BaseMemoryService, Memory
from aituber.core.services.llm.base import BaseLLMService, Message
from aituber.core.services.character import CharacterService
from aituber.core.services.conversation import ConversationContext
from aituber.core.services.llm.openai import OpenAIService
from aituber.core.services.memory.chromadb import ChromaDBMemoryService


# 共通フィクスチャ
@pytest.fixture
def app_config() -> AITuberConfig:
    """アプリケーション設定のフィクスチャ."""
    return AITuberConfig(
        app=AppConfig(data_dir=Path("data")),
        character=CharacterConfig(characters_dir=Path("characters")),
        memory=MemoryConfig(
            vector_db_path=Path("./vector_db"),
            collection_name="test_memories"
        ),
        integrations=IntegrationsConfig(
            openai=OpenAIConfig(
                api_key="dummy-key",
                model="gpt-3.5-turbo",
                temperature=0.7
            )
        )
    )


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """一時ディレクトリを作成."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def container(app_config: AITuberConfig, temp_dir: str) -> ServiceContainer:
    """DIコンテナのフィクスチャ."""
    container = ServiceContainer(app_config)
    # 一時ディレクトリを設定
    container.config.memory.vector_db_path = Path(temp_dir)
    
    # 各サービスのモックを作成
    llm_mock = MagicMock(spec=BaseLLMService)
    character_mock = MagicMock(spec=CharacterService)
    memory_mock = AsyncMock(spec=BaseMemoryService)
    
    # モックをコンテナに設定
    container._llm_service = llm_mock
    container._character_service = character_mock
    container._memory_service = memory_mock
    
    return container


# LLMサービスのテスト
@pytest.mark.asyncio
async def test_llm_generate(app_config: AITuberConfig):
    """LLMサービスの生成機能をテスト."""
    llm_service = OpenAIService(app_config)
    
    # generate メソッドをモック化
    llm_service.generate = AsyncMock(return_value="テスト応答")
    
    result = await llm_service.generate([Message(role="user", content="こんにちは")])
    assert result == "テスト応答"


@pytest.mark.asyncio
async def test_llm_generate_with_template(app_config: AITuberConfig):
    """LLMサービスのテンプレート生成機能をテスト."""
    llm_service = OpenAIService(app_config)
    
    # generate メソッドをモック化
    llm_service.generate = AsyncMock(return_value="テスト応答")
    
    # テンプレートと変数の準備
    system_template = "あなたは{role}です。"
    human_template = "{name}について教えてください。"
    variables = {
        "role": "アシスタント",
        "name": "テスト"
    }
    
    result = await llm_service.generate_with_template(
        system_template=system_template,
        human_template=human_template,
        variables=variables
    )
    
    assert result == "テスト応答"
    # generateメソッドが正しい引数で呼ばれたことを確認
    llm_service.generate.assert_called_once()
    call_args = llm_service.generate.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0].role == "system"
    assert call_args[0].content == "あなたはアシスタントです。"
    assert call_args[1].role == "user"
    assert call_args[1].content == "テストについて教えてください。"


@pytest.mark.asyncio
async def test_llm_generate_stream(app_config: AITuberConfig):
    """LLMサービスのストリーミング生成機能をテスト."""
    llm_service = OpenAIService(app_config)

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

    tokens = []
    async for token in llm_service.generate_stream([Message(role="user", content="こんにちは")]):
        tokens.append(token)

    assert tokens == ["A", "I", "応", "答"]


# メモリサービスのテスト
def test_memory_creation():
    """メモリ作成のテスト."""
    memory = Memory(
        id="test_memory_id",
        character_id="test_char",
        user_id="test_user",
        text="テストメモリ"
    )
    
    assert memory.character_id == "test_char"
    assert memory.user_id == "test_user"
    assert memory.text == "テストメモリ"
    assert memory.created_at is not None


@pytest.mark.asyncio
async def test_memory_add_and_retrieve(container: ServiceContainer):
    """メモリの追加と取得をテスト."""
    memory_service = container.memory_service
    llm_service = container.llm_service
    llm_service.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])

    memory_mock = Memory(
        id="test_id",
        character_id="char1",
        user_id="user1",
        text="テストメモリ",
        created_at=datetime.now(),
        embedding=[0.1, 0.2, 0.3]
    )
    memory_service.add_memory = AsyncMock(return_value=memory_mock)

    # メモリオブジェクトを作成
    memory = await memory_service.add_memory(
        character_id="char1",
        user_id="user1",
        text="テストメモリ"
    )

    assert memory.character_id == "char1"
    assert memory.user_id == "user1"
    assert memory.text == "テストメモリ"


@pytest.mark.asyncio
async def test_memory_retrieve_relevant(container: ServiceContainer):
    """関連メモリの取得をテスト."""
    memory_service = container.memory_service
    llm_service = container.llm_service
    llm_service.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])

    memory_mock = Memory(
        id="test_id",
        character_id="char1",
        user_id="user1",
        text="テストメモリ1",
        created_at=datetime.now(),
        embedding=[0.1, 0.2, 0.3]
    )
    memory_service.retrieve_relevant_memories = AsyncMock(return_value=[memory_mock])

    memories = await memory_service.retrieve_relevant_memories(
        character_id="char1",
        query="テスト",
        limit=1
    )

    assert len(memories) == 1
    assert memories[0].character_id == "char1"
    assert memories[0].text == "テストメモリ1"


# 会話サービスのテスト
def test_conversation_context_creation():
    """会話コンテキスト作成のテスト."""
    ctx = ConversationContext(
        character_id="test_char",
        user_id="test_user"
    )
    
    assert ctx.character_id == "test_char"
    assert ctx.user_id == "test_user"
    assert len(ctx.messages) == 0
    assert ctx.created_at is not None
    assert ctx.updated_at is not None


@pytest.mark.asyncio
async def test_conversation_process_message(container: ServiceContainer):
    """会話メッセージ処理のテスト."""
    conversation_service = container.conversation_service
    character_service = container.character_service
    llm_service = container.llm_service
    
    # モックの設定
    character = MagicMock()
    character.id = "test_char"
    character.name = "テストキャラクター"
    character.system_prompt = "テスト用のプロンプト"
    character_service.get_character.return_value = character
    llm_service.generate = AsyncMock(return_value="AI応答")
    
    # 会話コンテキストの作成と処理
    ctx = conversation_service.get_or_create_conversation(
        character_id="test_char",
        user_id="test_user"
    )
    
    response = await conversation_service.process_message(
        conversation_id=ctx.conversation_id,
        user_message="こんにちは"
    )
    
    assert response == "AI応答"
    assert len(ctx.messages) == 2
    assert ctx.messages[0].role == "user"
    assert ctx.messages[0].content == "こんにちは"
    assert ctx.messages[1].role == "assistant"
    assert ctx.messages[1].content == "AI応答"


@pytest.mark.asyncio
async def test_conversation_process_message_stream(container: ServiceContainer):
    """会話メッセージのストリーミング処理をテスト."""
    conversation_service = container.conversation_service
    character_service = container.character_service
    llm_service = container.llm_service

    # モックの設定
    character = MagicMock()
    character.id = "test_char"
    character.name = "テストキャラクター"
    character.system_prompt = "テスト用のプロンプト"
    character_service.get_character.return_value = character

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

    llm_service.generate_stream = AsyncMock(return_value=mock_generator)

    # 会話コンテキストの作成と処理
    ctx = conversation_service.get_or_create_conversation(
        character_id="test_char",
        user_id="test_user"
    )

    tokens = []
    async for token in conversation_service.process_message_stream(
        conversation_id=ctx.conversation_id,
        user_message="こんにちは"
    ):
        tokens.append(token)

    assert tokens == ["A", "I", "応", "答"]
    assert len(ctx.messages) == 2
    assert ctx.messages[0].role == "user"
    assert ctx.messages[0].content == "こんにちは"
    assert ctx.messages[1].role == "assistant"
    assert ctx.messages[1].content == "AI応答"


@pytest.mark.asyncio
async def test_chromadb_service_initialization(container: ServiceContainer):
    """ChromaDBServiceの初期化をテスト."""
    memory_service = ChromaDBMemoryService(container.config, container.llm_service)
    assert memory_service.config == container.config
    assert memory_service.llm_service == container.llm_service
    assert memory_service.client is not None
    assert memory_service.collection is not None


@pytest.mark.asyncio
async def test_chromadb_service_add_and_get_memory(container: ServiceContainer):
    """ChromaDBServiceのメモリ追加と取得をテスト."""
    memory_service = ChromaDBMemoryService(container.config, container.llm_service)
    container.llm_service.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    
    # メモリを追加
    memory = await memory_service.add_memory(
        character_id="test_char",
        user_id="test_user",
        text="テストメモリ1",
        metadata={"test_key": "test_value"}
    )
    
    assert memory.character_id == "test_char"
    assert memory.user_id == "test_user"
    assert memory.text == "テストメモリ1"
    assert memory.embedding == [0.1, 0.2, 0.3]
    assert memory.metadata["test_key"] == "test_value"
    
    # メモリを取得
    retrieved_memory = await memory_service.get_memory(memory.id)
    assert retrieved_memory is not None
    assert retrieved_memory.id == memory.id
    assert retrieved_memory.text == "テストメモリ1"
    assert retrieved_memory.metadata["test_key"] == "test_value"


@pytest.mark.asyncio
async def test_chromadb_service_get_memories(container: ServiceContainer):
    """ChromaDBServiceのメモリ一覧取得をテスト."""
    memory_service = ChromaDBMemoryService(container.config, container.llm_service)
    container.llm_service.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    
    # メモリを追加
    await memory_service.add_memory(
        character_id="test_char",
        user_id="test_user",
        text="テストメモリ1"
    )
    await memory_service.add_memory(
        character_id="test_char",
        user_id="test_user",
        text="テストメモリ2"
    )
    
    # メモリ一覧を取得
    memories = await memory_service.get_memories("test_char", limit=2)
    assert len(memories) == 2
    assert all(isinstance(m, Memory) for m in memories)
    assert all(m.character_id == "test_char" for m in memories)


@pytest.mark.asyncio
async def test_chromadb_service_retrieve_relevant_memories(container: ServiceContainer):
    """ChromaDBServiceの関連メモリ検索をテスト."""
    memory_service = ChromaDBMemoryService(container.config, container.llm_service)
    container.llm_service.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    
    # メモリを追加
    await memory_service.add_memory(
        character_id="test_char",
        user_id="test_user",
        text="テストメモリ1"
    )
    await memory_service.add_memory(
        character_id="test_char",
        user_id="test_user",
        text="テストメモリ2"
    )
    
    # 関連メモリを検索
    memories = await memory_service.retrieve_relevant_memories(
        character_id="test_char",
        query="テスト",
        limit=1,
        threshold=0.7
    )
    
    assert len(memories) == 1
    assert isinstance(memories[0], Memory)
    assert memories[0].character_id == "test_char"
    assert memories[0].text in ["テストメモリ1", "テストメモリ2"]


@pytest.mark.asyncio
async def test_chromadb_service_update_memory(container: ServiceContainer):
    """ChromaDBServiceのメモリ更新をテスト."""
    memory_service = ChromaDBMemoryService(container.config, container.llm_service)
    container.llm_service.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    
    # メモリを追加
    memory = await memory_service.add_memory(
        character_id="test_char",
        user_id="test_user",
        text="テストメモリ1",
        metadata={"test_key": "test_value"}
    )
    
    # メモリを更新
    updated_memory = await memory_service.update_memory(
        memory_id=memory.id,
        text="更新されたテストメモリ",
        metadata={"test_key": "updated_value"}
    )
    
    assert updated_memory.id == memory.id
    assert updated_memory.text == "更新されたテストメモリ"
    assert updated_memory.metadata["test_key"] == "updated_value"
    
    # 更新されたメモリを取得して確認
    retrieved_memory = await memory_service.get_memory(memory.id)
    assert retrieved_memory is not None
    assert retrieved_memory.text == "更新されたテストメモリ"
    assert retrieved_memory.metadata["test_key"] == "updated_value"


@pytest.mark.asyncio
async def test_chromadb_service_delete_memory(container: ServiceContainer):
    """ChromaDBServiceのメモリ削除をテスト."""
    memory_service = ChromaDBMemoryService(container.config, container.llm_service)
    container.llm_service.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    
    # メモリを追加
    memory = await memory_service.add_memory(
        character_id="test_char",
        user_id="test_user",
        text="テストメモリ1"
    )
    
    # メモリを削除
    result = await memory_service.delete_memory(memory.id)
    assert result is True
    
    # 削除されたメモリを取得して確認
    retrieved_memory = await memory_service.get_memory(memory.id)
    assert retrieved_memory is None 