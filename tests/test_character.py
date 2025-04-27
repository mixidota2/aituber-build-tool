"""キャラクター機能のテスト."""

import os
import tempfile
import pytest
from aituber.character.models import Character, Persona, PersonalityTrait, Interest
from aituber.character.storage import FileSystemCharacterStorage
from aituber.character.manager import CharacterManager
from aituber.core.context import AppContext
from aituber.core.config import AITuberConfig, CharacterConfig


@pytest.fixture
def character_config():
    """キャラクター設定のフィクスチャ."""
    return CharacterConfig(characters_dir="characters")


@pytest.fixture
def temp_character_dir():
    """一時的なキャラクターディレクトリを作成."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_character():
    """サンプルキャラクターのフィクスチャ."""
    return Character(
        id="test_char",
        name="テストキャラクター",
        version="1.0.0",
        description="テスト用キャラクター",
        system_prompt="あなたはテスト用のキャラクターです。",
        persona=Persona(
            age=20,
            gender="非公開",
            occupation="テスター",
            background="テスト目的で作成されました。",
            appearance="特になし",
            speech_style="普通の話し方",
        ),
        personality_traits=[
            PersonalityTrait(
                name="真面目",
                description="テストに真面目に取り組みます。",
                strength=0.8,
            )
        ],
        interests=[
            Interest(
                name="テスト",
                description="ソフトウェアテストに興味があります。",
                level=0.9,
            )
        ],
    )


@pytest.fixture
def character_storage(temp_character_dir):
    """キャラクターストレージのフィクスチャ."""
    return FileSystemCharacterStorage(temp_character_dir)


@pytest.fixture
def app_context(character_config, temp_character_dir):
    """アプリケーションコンテキストのフィクスチャ."""
    config = AITuberConfig()
    config.character = character_config
    context = AppContext(config)
    
    # キャラクターストレージを登録
    storage = FileSystemCharacterStorage(temp_character_dir)
    context.register_service("character_storage", storage)
    
    return context


@pytest.fixture
def character_manager(app_context, character_storage):
    """キャラクターマネージャーのフィクスチャ."""
    manager = CharacterManager(app_context, character_storage)
    app_context.register_service("character_manager", manager)
    return manager


def test_character_creation():
    """キャラクター作成のテスト."""
    character = Character(
        id="test_id",
        name="Test Character",
        system_prompt="This is a test prompt",
        description="Test description",
    )
    
    assert character.id == "test_id"
    assert character.name == "Test Character"
    assert character.system_prompt == "This is a test prompt"
    assert character.description == "Test description"


def test_character_save_and_load(character_storage, sample_character):
    """キャラクターの保存と読み込みをテスト."""
    # キャラクターデータを辞書形式に変換して保存する必要がある
    character_data = sample_character.model_dump()
    character_storage.save_character(sample_character.id, character_data)
    
    # ファイルが存在することを確認
    expected_path = character_storage.get_character_path(sample_character.id)
    assert os.path.exists(expected_path)
    
    # 読み込み
    loaded_data = character_storage.get_character(sample_character.id)
    loaded_character = Character.model_validate(loaded_data)
    
    # 内容を検証
    assert loaded_character.id == sample_character.id
    assert loaded_character.name == sample_character.name
    assert loaded_character.description == sample_character.description
    assert loaded_character.system_prompt == sample_character.system_prompt


def test_character_list(character_storage, sample_character):
    """キャラクター一覧取得のテスト."""
    # キャラクターを保存
    character_storage.save_character(sample_character.id, sample_character.model_dump())
    
    # 別のキャラクターも保存
    second_character = Character(
        id="test_char2",
        name="テストキャラクター2",
        version="1.0.0",
        description="2つ目のテスト用キャラクター",
        system_prompt="あなたは2つ目のテスト用キャラクターです。",
    )
    character_storage.save_character(second_character.id, second_character.model_dump())
    
    # 一覧を取得
    character_ids = character_storage.list_characters()
    
    # 2つのキャラクターが取得できることを検証
    assert len(character_ids) == 2
    assert "test_char" in character_ids
    assert "test_char2" in character_ids


def test_character_manager(character_manager, sample_character):
    """キャラクターマネージャーのテスト."""
    # キャラクターを作成
    character_manager.create_character(sample_character)
    
    # キャラクターを読み込み
    loaded_character = character_manager.load_character(sample_character.id)
    assert loaded_character.id == sample_character.id
    
    # アクティブキャラクターとして設定
    character_manager.set_active_character(sample_character.id)
    active_character = character_manager.get_active_character()
    assert active_character.id == sample_character.id
    
    # キャラクター一覧を取得
    characters = character_manager.list_characters()
    assert len(characters) == 1
    assert characters[0].id == sample_character.id 