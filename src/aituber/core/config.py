"""Configuration management for AITuber framework."""

import os
import yaml
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from pathlib import Path


def resolve_data_path(data_dir: str, relative_path: str) -> str:
    """
    アプリケーションのデータディレクトリからの相対パスを解決する

    Args:
        data_dir: ベースとなるデータディレクトリ
        relative_path: data_dirからの相対パス

    Returns:
        解決された絶対パス
    """
    return os.path.join(data_dir, relative_path)


class AppConfig(BaseModel):
    """アプリケーション基本設定"""

    debug: bool = False
    data_dir: Path = Field(default=Path("data"))


class OpenAIConfig(BaseModel):
    """OpenAI設定"""

    api_key: str = ""
    organization: Optional[str] = None
    model: str = "gpt-4-turbo-preview"
    embedding_model: str = "text-embedding-3-small"
    temperature: float = 0.7
    max_tokens: int = 1000
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0


class StorageConfig(BaseModel):
    """ストレージ設定"""

    local_path: Path = Field(default=Path("data/storage"))


class MemoryConfig(BaseModel):
    """メモリ設定"""

    vector_db_path: Path = Field(default=Path("data/vector_db"))
    collection_name: str = "memories"


class CharacterConfig(BaseModel):
    """キャラクター設定"""

    characters_dir: Path = Field(default=Path("data/characters"))


class IntegrationsConfig(BaseModel):
    """外部サービス統合設定"""

    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)


class AITuberConfig(BaseModel):
    """アプリケーション全体設定"""

    app: AppConfig = Field(default_factory=AppConfig)
    character: CharacterConfig = Field(default_factory=CharacterConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    integrations: IntegrationsConfig = Field(default_factory=IntegrationsConfig)


class ConfigManager:
    """設定管理クラス"""

    def __init__(self, config_path: str = "config.yaml"):
        """初期化

        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path

    def load_config(self) -> AITuberConfig:
        """設定ファイルを読み込む

        Returns:
            AITuberConfig: 読み込まれた設定
        """
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_dict = yaml.safe_load(f)
            return AITuberConfig(**config_dict)
        except Exception as e:
            print(f"設定ファイルの読み込みに失敗しました: {e}")
            return AITuberConfig()

    def save_config(self, config: AITuberConfig) -> None:
        """設定をファイルに保存する"""
        config_data = config.model_dump()

        os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True, sort_keys=False)

    def get_config(self) -> AITuberConfig:
        """現在の設定を取得する (必要に応じて読み込み)"""
        return self.load_config()

    def update_config(self, updates: Dict[str, Any]) -> AITuberConfig:
        """設定を更新する"""
        config = self.get_config()
        config_data = config.model_dump()

        # 設定の更新（ネストした辞書もサポート）
        def update_nested_dict(target, source):
            for key, value in source.items():
                if (
                    isinstance(value, dict)
                    and key in target
                    and isinstance(target[key], dict)
                ):
                    update_nested_dict(target[key], value)
                else:
                    target[key] = value

        update_nested_dict(config_data, updates)

        updated_config = AITuberConfig(**config_data)
        self.save_config(updated_config)

        return updated_config
