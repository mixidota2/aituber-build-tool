"""アプリケーションの例外定義"""


class AITuberError(Exception):
    """AITuberアプリケーションの基本例外"""

    pass


class LLMError(AITuberError):
    """LLM関連の例外"""

    pass


class MemoryError(AITuberError):
    """メモリ関連の例外"""

    pass


class CharacterError(AITuberError):
    """キャラクター関連の例外"""

    pass


class IntegrationError(AITuberError):
    """外部サービス連携関連の例外"""

    pass


class ConfigError(AITuberError):
    """設定関連のエラー"""

    pass


class StorageError(AITuberError):
    """ストレージ関連のエラー"""

    pass


class APIError(AITuberError):
    """API関連のエラー"""

    pass
