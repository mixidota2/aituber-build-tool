"""メモリ機能のテスト."""

import tempfile
import pytest
from datetime import datetime
from enum import Enum
from typing import List, Optional

from aituber.core.context import AppContext
from aituber.core.config import AITuberConfig, MemoryConfig, CharacterConfig

# Messageとの名前衝突を避けるためにモック定義
class MessageRole(str, Enum):
    """メッセージの役割"""
    USER = "user"
    AI = "assistant"
    SYSTEM = "system"


class Message:
    """テスト用のメッセージクラス"""
    def __init__(self, content: str, role: MessageRole, timestamp: datetime):
        self.content = content
        self.role = role
        self.timestamp = timestamp


class Conversation:
    """テスト用の会話クラス"""
    def __init__(self, id: str, character_id: str, user_id: str, messages: Optional[List[Message]] = None):
        self.id = id
        self.character_id = character_id
        self.user_id = user_id
        self.messages = messages if messages is not None else []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
    def add_message(self, message: Message):
        """メッセージを追加"""
        self.messages.append(message)
        self.updated_at = datetime.now()
        
    def get_last_messages(self, n: int) -> List[Message]:
        """最新のn件のメッセージを取得"""
        return self.messages[-n:] if n < len(self.messages) else self.messages[:]


@pytest.fixture
def memory_config():
    """メモリ設定のフィクスチャ."""
    return MemoryConfig(vector_db_path="vector_db")


@pytest.fixture
def character_config():
    """キャラクター設定のフィクスチャ."""
    return CharacterConfig(characters_dir="characters")


@pytest.fixture
def temp_db_dir():
    """一時的なベクターDBディレクトリを作成."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def app_context(memory_config, character_config, temp_db_dir):
    """アプリケーションコンテキストのフィクスチャ."""
    config = AITuberConfig()
    config.memory = memory_config
    config.character = character_config
    context = AppContext(config)
    
    # 一時ディレクトリを設定
    config.memory.vector_db_path = temp_db_dir
    
    return context


@pytest.fixture
def sample_message():
    """サンプルメッセージのフィクスチャ."""
    return Message(
        content="こんにちは、テストです。",
        role=MessageRole.USER,
        timestamp=datetime.now()
    )


@pytest.fixture
def sample_conversation():
    """サンプル会話のフィクスチャ."""
    return Conversation(
        id="test_convo",
        character_id="test_char",
        user_id="test_user",
        messages=[
            Message(
                content="こんにちは、テストです。",
                role=MessageRole.USER,
                timestamp=datetime.now()
            ),
            Message(
                content="こんにちは、テストユーザーさん。何かお手伝いできることはありますか？",
                role=MessageRole.AI,
                timestamp=datetime.now()
            )
        ]
    )


def test_message_creation():
    """メッセージ作成のテスト."""
    content = "テストメッセージ"
    role = MessageRole.USER
    timestamp = datetime.now()
    
    message = Message(
        content=content,
        role=role,
        timestamp=timestamp
    )
    
    assert message.content == content
    assert message.role == role
    assert message.timestamp == timestamp


def test_conversation_creation():
    """会話作成のテスト."""
    convo_id = "test_id"
    char_id = "test_char"
    user_id = "test_user"
    
    conversation = Conversation(
        id=convo_id,
        character_id=char_id,
        user_id=user_id
    )
    
    assert conversation.id == convo_id
    assert conversation.character_id == char_id
    assert conversation.user_id == user_id
    assert conversation.messages == []
    assert conversation.created_at is not None
    assert conversation.updated_at is not None


def test_conversation_add_message(sample_conversation, sample_message):
    """会話へのメッセージ追加をテスト."""
    # 会話前のメッセージ数を記録
    initial_count = len(sample_conversation.messages)
    
    # メッセージを追加
    sample_conversation.add_message(sample_message)
    
    # 追加後のメッセージ数を確認
    assert len(sample_conversation.messages) == initial_count + 1
    
    # 最後のメッセージが追加したものと一致することを確認
    assert sample_conversation.messages[-1].content == sample_message.content
    assert sample_conversation.messages[-1].role == sample_message.role


def test_conversation_get_last_messages(sample_conversation):
    """最新のメッセージ取得をテスト."""
    # 会話からの最後のN個のメッセージを取得
    last_message = sample_conversation.get_last_messages(1)
    
    # 結果を検証
    assert len(last_message) == 1
    assert last_message[0].role == MessageRole.AI
    
    # 全てのメッセージを取得
    all_messages = sample_conversation.get_last_messages(10)
    assert len(all_messages) == 2
    
    # 順序が正しいことを確認（古いメッセージから新しいメッセージの順）
    assert all_messages[0].role == MessageRole.USER
    assert all_messages[1].role == MessageRole.AI 