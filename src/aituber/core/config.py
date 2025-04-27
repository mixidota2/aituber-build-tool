"""Configuration management for AITuber framework."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import yaml
import os


class AppConfig(BaseModel):
    """アプリケーション全体の設定"""

    debug_mode: bool = False
    log_level: str = "INFO"
    data_dir: str = "./data"


class LLMConfig(BaseModel):
    """LLM関連の設定"""

    provider: str = "openai"  # openai, anthropic, etc.
    model: str = "gpt-4-turbo"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0


class CharacterConfig(BaseModel):
    """キャラクター関連の設定"""

    characters_dir: str = "characters"
    default_character: Optional[str] = None


class MemoryConfig(BaseModel):
    """記憶システム関連の設定"""

    vector_db_path: str = "vector_db"
    embedding_model: str = "text-embedding-3-small"


class IntegrationsConfig(BaseModel):
    """統合機能の設定"""

    voice_enabled: bool = False
    x_enabled: bool = False
    youtube_enabled: bool = False

    voice_settings: Dict[str, Any] = Field(default_factory=dict)
    x_settings: Dict[str, Any] = Field(default_factory=dict)
    youtube_settings: Dict[str, Any] = Field(default_factory=dict)


class AITuberConfig(BaseModel):
    """アプリケーション全体の設定モデル"""

    app: AppConfig = Field(default_factory=AppConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    character: CharacterConfig = Field(default_factory=CharacterConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    integrations: IntegrationsConfig = Field(default_factory=IntegrationsConfig)


class ConfigManager:
    """設定の読み込みと管理を行うクラス"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self._config: Optional[AITuberConfig] = None

    def load_config(self) -> AITuberConfig:
        """設定ファイルを読み込む"""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
        else:
            config_data = {}

        self._config = AITuberConfig.model_validate(config_data)
        return self._config

    def save_config(self, config: AITuberConfig) -> None:
        """設定をファイルに保存する"""
        config_data = config.model_dump()

        os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True, sort_keys=False)

        self._config = config

    def get_config(self) -> AITuberConfig:
        """現在の設定を取得する (必要に応じて読み込み)"""
        if self._config is None:
            return self.load_config()
        return self._config

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

        updated_config = AITuberConfig.model_validate(config_data)
        self.save_config(updated_config)

        return updated_config
