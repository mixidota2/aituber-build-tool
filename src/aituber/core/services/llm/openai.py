"""OpenAIサービスの実装"""

from typing import List, Dict, Any, AsyncGenerator, cast, Literal
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from ....core.config import AITuberConfig
from .base import BaseLLMService, Message


class OpenAIService(BaseLLMService):
    """OpenAIサービスの実装"""

    def __init__(self, config: AITuberConfig):
        """初期化

        Args:
            config: アプリケーション設定
        """
        self.config = config
        self.client = AsyncOpenAI(
            api_key=self.config.integrations.openai.api_key,
            organization=self.config.integrations.openai.organization
        )

    def _convert_messages(self, messages: List[Message]) -> List[ChatCompletionMessageParam]:
        """メッセージをOpenAI APIの形式に変換"""
        converted_messages = []
        for msg in messages:
            message: ChatCompletionMessageParam = {
                "role": cast(Literal["system", "user", "assistant", "tool", "function"], msg.role),
                "content": msg.content
            }
            if msg.name:
                message["name"] = msg.name
            converted_messages.append(message)
        return converted_messages

    async def generate(self, messages: List[Message], **kwargs) -> str:
        """メッセージからテキスト生成"""
        response = await self.client.chat.completions.create(
            model=self.config.integrations.openai.model,
            messages=self._convert_messages(messages),
            temperature=self.config.integrations.openai.temperature,
            max_tokens=self.config.integrations.openai.max_tokens,
            presence_penalty=self.config.integrations.openai.presence_penalty,
            frequency_penalty=self.config.integrations.openai.frequency_penalty,
            **kwargs
        )
        content = cast(ChatCompletion, response).choices[0].message.content
        if content is None:
            raise ValueError("OpenAI APIから空の応答が返されました")
        return content

    async def generate_with_template(
        self,
        system_template: str,
        human_template: str,
        variables: Dict[str, Any],
        **kwargs
    ) -> str:
        """テンプレートを使用したテキスト生成"""
        messages = [
            Message(role="system", content=system_template.format(**variables)),
            Message(role="user", content=human_template.format(**variables))
        ]
        return await self.generate(messages, **kwargs)

    async def generate_stream(self, messages: List[Message], **kwargs) -> AsyncGenerator[str, None]:
        """ストリーミングテキスト生成"""
        stream = await self.client.chat.completions.create(
            model=self.config.integrations.openai.model,
            messages=self._convert_messages(messages),
            temperature=self.config.integrations.openai.temperature,
            max_tokens=self.config.integrations.openai.max_tokens,
            presence_penalty=self.config.integrations.openai.presence_penalty,
            frequency_penalty=self.config.integrations.openai.frequency_penalty,
            stream=True,
            **kwargs
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    async def get_embeddings(self, texts: List[str], **kwargs) -> List[List[float]]:
        """テキストの埋め込みベクトルを取得"""
        response = await self.client.embeddings.create(
            model=self.config.integrations.openai.embedding_model,
            input=texts,
            **kwargs
        )
        return [embedding.embedding for embedding in response.data] 