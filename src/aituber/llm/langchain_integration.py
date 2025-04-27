"""LangChain integration for AITuber framework."""

from typing import List, Dict, Any, Optional, AsyncIterator
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel, SecretStr

from langchain_openai import ChatOpenAI
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_openai import OpenAIEmbeddings
from langchain.chains.llm import LLMChain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from ..core.context import AppContext
from ..core.exceptions import LLMError


class Message(BaseModel):
    """対話メッセージ"""

    role: str  # "system", "user", "assistant"
    content: str

    def to_langchain_message(self) -> BaseMessage:
        """LangChainメッセージ形式に変換"""
        if self.role == "system":
            return SystemMessage(content=self.content)
        elif self.role == "user":
            return HumanMessage(content=self.content)
        elif self.role == "assistant":
            return AIMessage(content=self.content)
        else:
            raise ValueError(f"未サポートのメッセージロール: {self.role}")


class StreamingCallbackHandler(BaseCallbackHandler):
    """ストリーミング出力用コールバック"""

    def __init__(self):
        self.tokens = []

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """新しいトークンが生成されたときのコールバック"""
        self.tokens.append(token)


class LangChainService:
    """LangChainを使用したLLMサービス"""

    def __init__(self, app_context: AppContext):
        self.app_context = app_context
        self.config = app_context.config.llm

        # 環境変数からAPIキーを取得
        import os

        api_key_str = self.config.api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key_str:
            raise LLMError("OpenAI API キーが設定されていません")
        
        # SecretStrに変換
        secret_api_key = SecretStr(api_key_str)

        # LLMモデルの初期化
        self.chat_model = ChatOpenAI(
            model=self.config.model,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            presence_penalty=self.config.presence_penalty,
            frequency_penalty=self.config.frequency_penalty,
            api_key=secret_api_key,
            streaming=False,
        )

        # ストリーミング用モデル
        self.streaming_model = ChatOpenAI(
            model=self.config.model,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            presence_penalty=self.config.presence_penalty,
            frequency_penalty=self.config.frequency_penalty,
            api_key=secret_api_key,
            streaming=True,
        )

        # 埋め込みモデル
        self.embeddings = OpenAIEmbeddings(
            model=self.app_context.config.memory.embedding_model, 
            api_key=secret_api_key
        )

    async def generate(self, messages: List[Message]) -> str:
        """メッセージからテキスト生成"""
        try:
            langchain_messages = [msg.to_langchain_message() for msg in messages]
            response = await self.chat_model.agenerate([langchain_messages])
            return response.generations[0][0].text
        except Exception as e:
            raise LLMError(f"テキスト生成中にエラーが発生しました: {e}")

    async def generate_with_template(
        self, system_template: str, human_template: str, variables: Dict[str, Any]
    ) -> str:
        """テンプレートを使用したテキスト生成"""
        try:
            chat_prompt = ChatPromptTemplate.from_messages(
                [("system", system_template), ("human", human_template)]
            )
            chain = LLMChain(llm=self.chat_model, prompt=chat_prompt)
            response = await chain.arun(**variables)
            return response
        except Exception as e:
            raise LLMError(
                f"テンプレートを使用したテキスト生成中にエラーが発生しました: {e}"
            )

    async def generate_stream(self, messages: List[Message]) -> AsyncIterator[str]:
        """ストリーミングテキスト生成"""
        try:
            langchain_messages = [msg.to_langchain_message() for msg in messages]
            callback = StreamingCallbackHandler()

            # ストリーミング生成を別スレッドで実行
            async def _generate():
                with ThreadPoolExecutor() as executor:
                    await asyncio.get_event_loop().run_in_executor(
                        executor,
                        lambda: self.streaming_model.generate(
                            [langchain_messages], callbacks=[callback]
                        ),
                    )

            # 非同期生成開始
            generation_task = asyncio.create_task(_generate())

            # トークンバッファ
            sent_index = 0

            # トークンが出力されるまで待機
            while not generation_task.done() or sent_index < len(callback.tokens):
                # 新しいトークンがあればyield
                while sent_index < len(callback.tokens):
                    yield callback.tokens[sent_index]
                    sent_index += 1

                # 少し待機
                await asyncio.sleep(0.01)

        except Exception as e:
            raise LLMError(f"ストリーミングテキスト生成中にエラーが発生しました: {e}")

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """テキストの埋め込みベクトルを取得"""
        try:
            return await self.embeddings.aembed_documents(texts)
        except Exception as e:
            raise LLMError(f"埋め込みベクトル生成中にエラーが発生しました: {e}")

    def get_chain(
        self,
        system_template: str,
        human_template: Optional[str] = None,
        memory: Optional[Any] = None,
    ) -> LLMChain:
        """LangChainチェーンを取得"""
        try:
            # 新しいChatPromptTemplateの構造に合わせて作成
            prompt_messages = []
            prompt_messages.append(SystemMessage(content=system_template))

            if memory:
                prompt_messages.append(MessagesPlaceholder(variable_name="history"))

            if human_template:
                prompt_messages.append(HumanMessage(content=human_template))
            else:
                prompt_messages.append(MessagesPlaceholder(variable_name="input"))

            chat_prompt = ChatPromptTemplate.from_messages(prompt_messages)

            chain = LLMChain(llm=self.chat_model, prompt=chat_prompt, memory=memory)

            return chain
        except Exception as e:
            raise LLMError(f"チェーン作成中にエラーが発生しました: {e}")
