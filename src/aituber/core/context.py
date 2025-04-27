"""Application context for AITuber framework."""

from typing import Dict, Any, Optional, TypeVar, Type, cast
from .config import AITuberConfig
from .events import EventBus, Event, EventType

T = TypeVar("T")


class ServiceNotFoundError(Exception):
    """サービスが見つからない場合の例外"""

    pass


class AppContext:
    """アプリケーション全体で共有するコンテキスト"""

    def __init__(self, config: AITuberConfig):
        self.config = config
        self.event_bus = EventBus()
        self._services: Dict[str, Any] = {}

    def register_service(self, name: str, service: Any) -> None:
        """サービスの登録"""
        self._services[name] = service

    def get_service(self, name: str) -> Any:
        """サービスの取得"""
        if name not in self._services:
            raise ServiceNotFoundError(f"サービス '{name}' が登録されていません")
        return self._services[name]

    def get_service_of_type(self, service_type: Type[T]) -> T:
        """指定された型のサービスを取得"""
        for service in self._services.values():
            if isinstance(service, service_type):
                return cast(T, service)

        raise ServiceNotFoundError(
            f"型 '{service_type.__name__}' のサービスが見つかりません"
        )

    def has_service(self, name: str) -> bool:
        """指定された名前のサービスが存在するか確認"""
        return name in self._services

    def publish_event(
        self, event_type: EventType, data: Any = None, source: Optional[str] = None
    ) -> None:
        """イベントの発行"""
        event = Event(type=event_type, data=data, source=source)
        self.event_bus.publish(event)
