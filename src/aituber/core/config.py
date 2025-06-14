"""Configuration management for AITuber framework."""

import os
import re
import yaml
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from pathlib import Path

logger = logging.getLogger(__name__)


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

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """API key validation - must not be empty in production"""
        if not v or v.strip() == "":
            # Try to get from environment
            env_key = os.getenv('OPENAI_API_KEY', '')
            if env_key:
                return env_key
            logger.warning("OpenAI API key not provided - some features may not work")
        return v


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

    def _expand_env_vars(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """環境変数を展開する"""
        def expand_value(value):
            if isinstance(value, str):
                # ${VAR_NAME} or $VAR_NAME pattern
                pattern = r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)'
                def replace_env(match):
                    var_name = match.group(1) or match.group(2)
                    return os.getenv(var_name, match.group(0))
                return re.sub(pattern, replace_env, value)
            elif isinstance(value, dict):
                return {k: expand_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [expand_value(item) for item in value]
            return value
        
        return expand_value(config_dict)

    def load_config(self) -> AITuberConfig:
        """設定ファイルを読み込む

        Returns:
            AITuberConfig: 読み込まれた設定
        """
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Configuration file not found: {self.config_path}. Using defaults.")
                return AITuberConfig()
                
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_dict = yaml.safe_load(f)
                
            if config_dict is None:
                logger.warning(f"Empty configuration file: {self.config_path}. Using defaults.")
                return AITuberConfig()
                
            # Expand environment variables
            config_dict = self._expand_env_vars(config_dict)
            
            return AITuberConfig(**config_dict)
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {self.config_path}: {e}")
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            logger.error(f"Failed to load configuration from {self.config_path}: {e}")
            raise RuntimeError(f"Configuration loading failed: {e}")

    def save_config(self, config: AITuberConfig) -> None:
        """設定をファイルに保存する"""
        try:
            config_data = config.model_dump()
            
            config_dir = os.path.dirname(os.path.abspath(self.config_path))
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
                
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, allow_unicode=True, sort_keys=False)
                
            logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration to {self.config_path}: {e}")
            raise RuntimeError(f"Configuration saving failed: {e}")

    def get_config(self) -> AITuberConfig:
        """現在の設定を取得する (必要に応じて読み込み)"""
        return self.load_config()
    
    @staticmethod
    def validate_path_safety(file_path: str, base_path: str) -> bool:
        """パストラバーサル攻撃を防ぐためのパス検証"""
        try:
            # 絶対パスに変換
            abs_file_path = os.path.abspath(file_path)
            abs_base_path = os.path.abspath(base_path)
            
            # ベースパス以下にあるかチェック
            return abs_file_path.startswith(abs_base_path)
        except Exception:
            return False

    def update_config(self, updates: Dict[str, Any]) -> AITuberConfig:
        """設定を更新する"""
        try:
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
            
            logger.info("Configuration updated successfully")
            return updated_config
            
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            raise RuntimeError(f"Configuration update failed: {e}")
