"""Exception classes for AITuber framework."""


class AITuberError(Exception):
    """AITuberフレームワークの基本例外クラス"""

    pass


class ConfigError(AITuberError):
    """設定関連のエラー"""

    pass


class CharacterError(AITuberError):
    """キャラクター関連のエラー"""

    pass


class StorageError(AITuberError):
    """ストレージ関連のエラー"""

    pass


class LLMError(AITuberError):
    """LLM関連のエラー"""

    pass


class MemoryError(AITuberError):
    """記憶システム関連のエラー"""

    pass


class IntegrationError(AITuberError):
    """外部統合関連のエラー"""

    pass


class APIError(AITuberError):
    """API関連のエラー"""

    pass
