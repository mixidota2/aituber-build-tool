"""コアサービス層のテスト."""

import tempfile
import pytest
from typing import Generator, AsyncGenerator
from unittest.mock import MagicMock, AsyncMock

from aituber.core.config import (
    AITuberConfig,
    AppConfig,
    MemoryConfig,
    CharacterConfig,
    LLMConfig,
    IntegrationsConfig,
)
from aituber.core.container import Container
from aituber.core.services.memory import MemoryService, Memory
from aituber.core.services.llm import LLMService, Message as LLMMessage
from aituber.core.services.character import CharacterService
from aituber.core.services.conversation import ConversationService, ConversationContext
from aituber.integrations.openai.llm import OpenAILLMService
from aituber.integrations.chromadb.memory import ChromaDBService


# 共通フィクスチャ
@pytest.fixture
def app_config() -> AITuberConfig:
    """アプリケーション設定のフィクスチャ."""
    return AITuberConfig(
        app=AppConfig(data_dir="data"),
        character=CharacterConfig(characters_dir="characters"),
        llm=LLMConfig(
            model="gpt-3.5-turbo",
            api_key="dummy-key",
            temperature=0.7
        ),
        memory=MemoryConfig(
            vector_db_path="./vector_db",
            collection_name="test_memories"
        ),
        integrations=IntegrationsConfig()
    )


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """一時ディレクトリを作成."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def container(app_config: AITuberConfig, temp_dir: str) -> Container:
    """DIコンテナのフィクスチャ."""
    container = Container(app_config)
    # 一時ディレクトリを設定
    container.config.memory.vector_db_path = temp_dir
    
    # 各サービスのモックを作成
    llm_mock = MagicMock(spec=LLMService)
    character_mock = MagicMock(spec=CharacterService)
    memory_mock = AsyncMock(spec=MemoryService)
    
    # モックをコンテナに設定
    container._llm_service = llm_mock
    container._character_service = character_mock
    container._memory_service = memory_mock
    
    return container


# LLMサービスのテスト
@pytest.mark.asyncio
async def test_llm_generate(app_config: AITuberConfig):
    """LLMサービスの生成機能をテスト."""
    llm_service = OpenAILLMService(app_config)
    
    # generate メソッドをモック化
    llm_service.generate = AsyncMock(return_value="テスト応答")
    
    result = await llm_service.generate([LLMMessage(role="user", content="こんにちは")])
    assert result == "テスト応答"


@pytest.mark.asyncio
async def test_llm_generate_with_template(app_config: AITuberConfig):
    """LLMサービスのテンプレート生成機能をテスト."""
    llm_service = OpenAILLMService(app_config)
    
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
    llm_service = OpenAILLMService(app_config)

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
    async for token in llm_service.generate_stream([LLMMessage(role="user", content="こんにちは")]):
        tokens.append(token)

    assert tokens == ["A", "I", "応", "答"]


# メモリサービスのテスト
def test_memory_creation():
    """メモリ作成のテスト."""
    memory = Memory(
        character_id="test_char",
        user_id="test_user",
        text="テストメモリ"
    )
    
    assert memory.character_id == "test_char"
    assert memory.user_id == "test_user"
    assert memory.text == "テストメモリ"
    assert memory.created_at is not None


@pytest.mark.asyncio
async def test_memory_add_and_retrieve(container: Container):
    """メモリの追加と取得をテスト."""
    memory_service = MemoryService(container.config, container.llm_service)
    llm_service = container.llm_service
    llm_service.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    
    # メモリオブジェクトを作成
    memory = await memory_service.add_memory(
        character_id="char1",
        user_id="user1",
        text="テストメモリ"
    )
    
    assert memory.character_id == "char1"
    assert memory.text == "テストメモリ"
    assert memory.embedding == [0.1, 0.2, 0.3]
    
    memories = memory_service.get_memories("char1")
    assert len(memories) == 1
    assert memories[0].text == "テストメモリ"


@pytest.mark.asyncio
async def test_memory_retrieve_relevant(container: Container):
    """関連メモリの取得をテスト."""
    memory_service = MemoryService(container.config, container.llm_service)
    llm_service = container.llm_service
    llm_service.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    
    await memory_service.add_memory(
        character_id="char1",
        user_id="user1",
        text="テストメモリ1"
    )
    await memory_service.add_memory(
        character_id="char1",
        user_id="user1",
        text="テストメモリ2"
    )
    
    memories = await memory_service.retrieve_relevant_memories(
        character_id="char1",
        query="テスト",
        limit=1
    )
    
    assert len(memories) == 1
    assert memories[0].text in ["テストメモリ1", "テストメモリ2"]


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
async def test_conversation_process_message(container: Container):
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
async def test_conversation_process_message_stream(container: Container):
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

    llm_service.generate_stream = MagicMock(return_value=mock_generator)

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
async def test_chromadb_service_initialization(container: Container):
    """ChromaDBServiceの初期化をテスト."""
    memory_service = ChromaDBService(container.config, container.llm_service)
    assert isinstance(memory_service.config.memory, MemoryConfig)
    assert memory_service.llm_service == container.llm_service
    assert memory_service.client is not None
    assert memory_service.collection is not None


@pytest.mark.asyncio
async def test_chromadb_service_add_and_search(container: Container):
    """ChromaDBServiceのメモリ追加と検索をテスト."""
    memory_service = ChromaDBService(container.config, container.llm_service)
    container.llm_service.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    
    # メモリを追加
    await memory_service.add_memory(
        text="テストメモリ1",
        metadata={
            "timestamp": "2024-03-21T00:00:00",
            "character_id": "test_char",
            "source": "test",
            "additional_context": {"test": "value1"}
        }
    )
    await memory_service.add_memory(
        text="テストメモリ2",
        metadata={
            "timestamp": "2024-03-21T00:00:00",
            "character_id": "test_char",
            "source": "test",
            "additional_context": {"test": "value2"}
        }
    )
    
    # 類似メモリを検索
    results = await memory_service.search_similar("テスト", n_results=1)
    assert len(results) == 1
    assert isinstance(results[0]["text"], str)
    assert results[0]["text"] in ["テストメモリ1", "テストメモリ2"]
    assert isinstance(results[0]["metadata"], dict)
    assert results[0]["metadata"]["character_id"] == "test_char"
    
    # 最近のメモリを取得
    recent = await memory_service.get_recent(limit=2)
    assert len(recent) == 2
    assert isinstance(recent[0]["text"], str)
    assert recent[0]["text"] in ["テストメモリ1", "テストメモリ2"]
    assert isinstance(recent[0]["metadata"], dict)
    assert recent[0]["metadata"]["character_id"] == "test_char"
    
    # メモリをクリア
    await memory_service.clear()
    recent = await memory_service.get_recent()
    assert len(recent) == 0 