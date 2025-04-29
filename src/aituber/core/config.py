"""Configuration management for AITuber framework."""

import os
import yaml
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


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
    """アプリケーション全般の設定"""
    data_dir: str = "data"
    debug_mode: bool = False


class CharacterConfig(BaseModel):
    """キャラクター関連の設定"""
    characters_dir: str = "characters"


class LLMConfig(BaseModel):
    """LLM設定"""
    api_key: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    top_p: float = 1.0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0


class MemoryConfig(BaseModel):
    """メモリ設定"""
    embedding_model: str = "text-embedding-3-small"
    collection_name: str = "memories"
    vector_db_path: str = "./vector_db"


class IntegrationsConfig(BaseModel):
    """統合機能の設定"""
    voice_enabled: bool = False
    x_enabled: bool = False
    youtube_enabled: bool = False
    voice_settings: Dict[str, Any] = Field(default_factory=dict)
    x_settings: Dict[str, Any] = Field(default_factory=dict)
    youtube_settings: Dict[str, Any] = Field(default_factory=dict)


class AITuberConfig(BaseModel):
    """アプリケーション全体の設定"""
    app: AppConfig = Field(default_factory=AppConfig)
    character: CharacterConfig = Field(default_factory=CharacterConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    integrations: IntegrationsConfig = Field(default_factory=IntegrationsConfig)


class ConfigManager:
    """設定管理クラス"""

    def __init__(self, config_path: str):
        """
        設定管理クラスの初期化

        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path

    def load_config(self) -> AITuberConfig:
        """
        設定ファイルを読み込む

        Returns:
            AITuberConfig: 設定オブジェクト
        """
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            return AITuberConfig(**config_data)
        except FileNotFoundError:
            # 設定ファイルが存在しない場合はデフォルト値を使用
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
