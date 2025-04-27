"""Event system for AITuber framework."""

from typing import Dict, List, Callable, Any, Optional
from enum import Enum, auto
from dataclasses import dataclass


class EventType(Enum):
    """イベントの種類"""

    # 対話関連
    MESSAGE_RECEIVED = auto()  # メッセージ受信
    MESSAGE_PROCESSED = auto()  # メッセージ処理完了
    RESPONSE_GENERATED = auto()  # 応答生成
    RESPONSE_SENT = auto()  # 応答送信

    # キャラクター関連
    CHARACTER_LOADED = auto()  # キャラクター読み込み
    CHARACTER_SWITCHED = auto()  # キャラクター切替

    # メモリ関連
    MEMORY_ADDED = auto()  # 記憶追加
    MEMORY_RETRIEVED = auto()  # 記憶取得

    # 統合関連
    VOICE_INPUT_RECEIVED = auto()  # 音声入力
    VOICE_OUTPUT_READY = auto()  # 音声出力準備完了

    # システム関連
    ERROR_OCCURRED = auto()  # エラー発生
    SYSTEM_READY = auto()  # システム準備完了


@dataclass
class Event:
    """イベントデータ"""

    type: EventType
    data: Any = None
    source: Optional[str] = None


EventHandler = Callable[[Event], None]


class EventBus:
    """シンプルなイベントバス"""

    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """イベント購読"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """すべてのイベントを購読"""
        self._global_handlers.append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """イベント購読解除"""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def unsubscribe_all(self, handler: EventHandler) -> None:
        """すべてのイベント購読解除"""
        if handler in self._global_handlers:
            self._global_handlers.remove(handler)

    def publish(self, event: Event) -> None:
        """イベント発行"""
        # 特定イベントのハンドラ呼び出し
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error in event handler: {e}")

        # グローバルハンドラ呼び出し
        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"Error in global event handler: {e}")
