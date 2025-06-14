"""統一されたアプリケーションファクトリー"""

import os
from typing import Optional

from ..app import AITuberApp


class AppFactory:
    """アプリケーションインスタンスの統一管理クラス"""
    
    _instance: Optional[AITuberApp] = None
    _config_path: Optional[str] = None
    
    @classmethod
    async def get_app(cls, config_path: Optional[str] = None, force_reload: bool = False) -> AITuberApp:
        """
        統一されたアプリケーションインスタンス取得
        
        Args:
            config_path: 設定ファイルのパス。None の場合は環境変数またはデフォルトを使用
            force_reload: 強制的に新しいインスタンスを作成するかどうか
            
        Returns:
            AITuberApp: アプリケーションインスタンス
        """
        # 設定パスの決定
        resolved_config_path = cls._resolve_config_path(config_path)
        
        # インスタンスの再作成が必要かチェック
        if (cls._instance is None or 
            force_reload or 
            cls._config_path != resolved_config_path):
            
            cls._instance = await cls._create_app(resolved_config_path)
            cls._config_path = resolved_config_path
            
        return cls._instance
    
    @classmethod
    def _resolve_config_path(cls, config_path: Optional[str] = None) -> str:
        """設定ファイルパスを決定する優先順位付きロジック"""
        # 1. 明示的に指定されたパス
        if config_path:
            return config_path
            
        # 2. 環境変数
        env_config = os.getenv("AITUBER_CONFIG_PATH")
        if env_config:
            return env_config
            
        # 3. デフォルトパス
        return "config.yaml"
    
    @classmethod
    async def _create_app(cls, config_path: str) -> AITuberApp:
        """新しいアプリケーションインスタンスを作成"""
        try:
            app = AITuberApp(config_path)
            await app.initialize()
            return app
        except Exception as e:
            # ログを追加できるように
            print(f"Error creating app with config {config_path}: {e}")
            raise
    
    @classmethod
    def reset(cls) -> None:
        """インスタンスをリセット（主にテスト用）"""
        cls._instance = None
        cls._config_path = None
    
    @classmethod
    def is_initialized(cls) -> bool:
        """アプリケーションが初期化済みかチェック"""
        return cls._instance is not None


# 便利な関数として従来のインターフェースを提供
async def get_app(config_path: Optional[str] = None) -> AITuberApp:
    """従来のget_app()インターフェースの互換性維持"""
    return await AppFactory.get_app(config_path)