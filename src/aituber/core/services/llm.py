"""LLMサービスの実装"""

from typing import List, Dict, Any, AsyncGenerator, Protocol, runtime_checkable
from pydantic import BaseModel


class Message(BaseModel):
    """対話メッセージ"""
    role: str  # "system", "user", "assistant"
    content: str

@runtime_checkable
class LLMService(Protocol):
    """LLMサービスのインターフェース"""

    async def generate(self, messages: List[Message]) -> str:
        """メッセージからテキスト生成"""
        ...

    async def generate_with_template(
        self,
        system_template: str,
        human_template: str,
        variables: Dict[str, Any]
    ) -> str:
        """テンプレートを使用したテキスト生成"""
        ...

    async def generate_stream(self, messages: List[Message]) -> AsyncGenerator[str, None]:
        """ストリーミングテキスト生成"""
        ...

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """テキストの埋め込みベクトルを取得"""
        ... 