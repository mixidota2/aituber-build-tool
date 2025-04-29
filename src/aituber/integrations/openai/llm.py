"""OpenAI LLM service implementation."""

from typing import List, AsyncGenerator, Dict, Any, cast
import openai
from openai.types.chat import ChatCompletionMessageParam

from ...core.config import AITuberConfig
from ...core.services.llm import LLMService
from ...core.services.conversation import Message


class OpenAILLMService(LLMService):
    """OpenAI LLMサービス"""

    def __init__(self, config: AITuberConfig):
        """
        OpenAI LLMサービスの初期化

        Args:
            config: アプリケーション設定
        """
        self.config = config.llm
        self.memory_config = config.memory
        self.client = openai.AsyncOpenAI(api_key=self.config.api_key)

    async def generate(self, messages: List[Message]) -> str:
        """
        メッセージ列から応答を生成

        Args:
            messages: メッセージ列

        Returns:
            生成された応答テキスト
        """
        openai_messages = [
            cast(ChatCompletionMessageParam, {"role": msg.role, "content": msg.content})
            for msg in messages
        ]
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            presence_penalty=self.config.presence_penalty,
            frequency_penalty=self.config.frequency_penalty,
        )
        content = response.choices[0].message.content
        return content if content is not None else ""

    async def generate_with_template(
        self,
        system_template: str,
        human_template: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        テンプレートを使用したテキスト生成

        Args:
            system_template: システムプロンプトのテンプレート
            human_template: ユーザープロンプトのテンプレート
            variables: テンプレート変数の辞書

        Returns:
            生成された応答テキスト
        """
        # テンプレートに変数を適用
        system_prompt = system_template.format(**variables)
        human_prompt = human_template.format(**variables)

        # メッセージの作成
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=human_prompt)
        ]

        # 応答の生成
        return await self.generate(messages)

    async def generate_stream(self, messages: List[Message]) -> AsyncGenerator[str, None]:
        """
        メッセージ列からストリーミング応答を生成

        Args:
            messages: メッセージ列

        Yields:
            生成された応答テキストのトークン
        """
        openai_messages = [
            cast(ChatCompletionMessageParam, {"role": msg.role, "content": msg.content})
            for msg in messages
        ]
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            presence_penalty=self.config.presence_penalty,
            frequency_penalty=self.config.frequency_penalty,
            stream=True,
        )

        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        テキストの埋め込みベクトルを取得

        Args:
            texts: 埋め込みベクトルを生成するテキストのリスト

        Returns:
            埋め込みベクトルのリスト
        """
        response = await self.client.embeddings.create(
            model=self.memory_config.embedding_model,
            input=texts,
        )
        return [embedding.embedding for embedding in response.data] 