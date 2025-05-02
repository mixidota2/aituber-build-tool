"""LLMサービスの基底クラス定義"""

from typing import List, Dict, Any, Optional, AsyncGenerator
from abc import ABC, abstractmethod

from pydantic import BaseModel


class Message(BaseModel):
    """対話メッセージ"""
    role: str  # "system", "user", "assistant"
    content: str
    name: Optional[str] = None


class BaseLLMService(ABC):
    """LLMサービスの基底クラス"""

    @abstractmethod
    async def generate(self, messages: List[Message], **kwargs) -> str:
        """メッセージからテキスト生成"""
        pass

    @abstractmethod
    async def generate_with_template(
        self,
        system_template: str,
        human_template: str,
        variables: Dict[str, Any],
        **kwargs
    ) -> str:
        """テンプレートを使用したテキスト生成"""
        pass

    @abstractmethod
    async def generate_stream(self, messages: List[Message], **kwargs) -> AsyncGenerator[str, None]:
        """ストリーミングテキスト生成"""
        pass

    @abstractmethod
    async def get_embeddings(self, texts: List[str], **kwargs) -> List[List[float]]:
        """テキストの埋め込みベクトルを取得"""
        pass 