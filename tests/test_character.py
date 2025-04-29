"""キャラクター機能のテスト."""

import tempfile
import pytest
from pydantic import ValidationError
from aituber.core.services.character import Character, Persona, PersonalityTrait, Interest, CharacterService
from aituber.integrations.storage.character import FileSystemCharacterStorage
from aituber.core.container import Container
from aituber.core.config import (
    AITuberConfig,
    AppConfig,
    CharacterConfig,
    LLMConfig,
    MemoryConfig,
    IntegrationsConfig,
)
from aituber.core.exceptions import CharacterError


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
                score=0.8,
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
def container(character_config, temp_character_dir):
    """DIコンテナのフィクスチャ."""
    config = AITuberConfig(
        app=AppConfig(data_dir=temp_character_dir),
        character=character_config,
        llm=LLMConfig(),
        memory=MemoryConfig(),
        integrations=IntegrationsConfig()
    )
    return Container(config)


@pytest.fixture
def character_service(container):
    """キャラクターサービスのフィクスチャ."""
    return container.character_service


def test_character_creation():
    """キャラクター作成のテスト."""
    character = Character(
        id="test_id",
        name="Test Character",
        system_prompt="This is a test prompt",
        description="Test description",
        persona=Persona(),
    )
    
    assert character.id == "test_id"
    assert character.name == "Test Character"
    assert character.system_prompt == "This is a test prompt"
    assert character.description == "Test description"


def test_character_save_and_load(character_storage, sample_character):
    """キャラクターの保存と読み込みをテスト."""
    # キャラクターを保存
    character_storage.save(sample_character)
    
    # 読み込み
    loaded_character = character_storage.load(sample_character.id)
    
    # 内容を検証
    assert loaded_character.id == sample_character.id
    assert loaded_character.name == sample_character.name
    assert loaded_character.description == sample_character.description
    assert loaded_character.system_prompt == sample_character.system_prompt


def test_character_list(character_storage, sample_character):
    """キャラクター一覧取得のテスト."""
    # キャラクターを保存
    character_storage.save(sample_character)
    
    # 別のキャラクターも保存
    second_character = Character(
        id="test_char2",
        name="テストキャラクター2",
        description="2つ目のテスト用キャラクター",
        system_prompt="あなたは2つ目のテスト用キャラクターです。",
        persona=Persona(),
    )
    character_storage.save(second_character)
    
    # 一覧を取得
    character_ids = character_storage.list_characters()
    
    # 2つのキャラクターが取得できることを検証
    assert len(character_ids) == 2
    assert "test_char" in character_ids
    assert "test_char2" in character_ids


def test_character_service(character_service, sample_character):
    """キャラクターサービスのテスト."""
    # キャラクターを作成
    created_character = character_service.create_character(
        name=sample_character.name,
        description=sample_character.description,
        system_prompt=sample_character.system_prompt,
        persona=sample_character.persona,
        personality_traits=sample_character.personality_traits,
        interests=sample_character.interests,
    )
    
    # キャラクターを取得
    loaded_character = character_service.get_character(created_character.id)
    assert loaded_character.id == created_character.id
    
    # キャラクター一覧を取得
    characters = character_service.list_characters()
    assert len(characters) == 1
    assert characters[0].id == created_character.id 


def test_character_save_with_invalid_path(character_storage, sample_character):
    """無効なパスでのキャラクター保存テスト."""
    # 無効なパスを設定
    character_storage.base_dir = "/invalid/path"

    with pytest.raises(CharacterError) as exc_info:
        character_storage.save(sample_character)
    assert "保存先ディレクトリにアクセスできません" in str(exc_info.value)


def test_character_load_nonexistent(character_storage):
    """存在しないキャラクターの読み込みテスト."""
    with pytest.raises(CharacterError) as exc_info:
        character_storage.load("nonexistent_character")
    assert "キャラクターファイルが見つかりません" in str(exc_info.value)


def test_character_save_with_invalid_data(character_storage):
    """無効なデータでのキャラクター保存テスト."""
    try:
        invalid_character = Character(
            id="",  # 空のID
            name="テストキャラクター",
            description="テスト用キャラクター",
            system_prompt="あなたはテスト用のキャラクターです。",
            persona=Persona(),
        )
        pytest.fail("空のIDを持つキャラクターの作成が成功してしまいました")
    except ValidationError as e:
        assert "String should have at least 1 character" in str(e)


def test_character_list_with_empty_directory(temp_character_dir):
    """空のディレクトリでのキャラクター一覧取得テスト."""
    storage = FileSystemCharacterStorage(temp_character_dir)
    character_ids = storage.list_characters()
    
    assert len(character_ids) == 0


def test_character_save_with_duplicate_id(character_storage, sample_character):
    """重複IDでのキャラクター保存テスト."""
    # 1回目の保存
    character_storage.save(sample_character)
    
    # 同じIDで別のキャラクターを保存
    duplicate_character = Character(
        id=sample_character.id,
        name="重複キャラクター",
        description="重複テスト用",
        system_prompt="重複テスト用のプロンプト",
        persona=Persona(),
    )
    
    # 上書き保存が成功することを確認
    character_storage.save(duplicate_character)
    
    # 読み込んで内容を確認
    loaded_character = character_storage.load(sample_character.id)
    assert loaded_character.name == "重複キャラクター"


def test_character_save_with_special_characters(character_storage):
    """特殊文字を含むキャラクター保存テスト."""
    special_character = Character(
        id="special_test",
        name="特殊文字テスト!@#$%^&*()",
        description="特殊文字を含む説明!@#$%^&*()",
        system_prompt="特殊文字を含むプロンプト!@#$%^&*()",
        persona=Persona(),
    )
    
    character_storage.save(special_character)
    loaded_character = character_storage.load("special_test")
    
    assert loaded_character.name == "特殊文字テスト!@#$%^&*()"
    assert loaded_character.description == "特殊文字を含む説明!@#$%^&*()" 