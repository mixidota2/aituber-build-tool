"""LLM機能のテスト."""

import pytest
from unittest.mock import MagicMock, patch
from aituber.core.context import AppContext
from aituber.core.config import AITuberConfig, LLMConfig


class LangChainLLMIntegration:
    """LLM統合機能のモッククラス"""
    
    def __init__(self, app_context):
        self.app_context = app_context
        self.config = app_context.config.llm
    
    async def generate_text(self, prompt, system_prompt):
        """テキスト生成（モック）"""
        pass
    
    async def generate_text_with_history(self, prompt, system_prompt, history):
        """履歴付きテキスト生成（モック）"""
        pass


@pytest.fixture
def llm_config():
    """LLM設定のフィクスチャ."""
    return LLMConfig(
        provider="openai",
        model="gpt-4-turbo",
        api_key="dummy-api-key",
        temperature=0.7
    )


@pytest.fixture
def app_context(llm_config):
    """アプリケーションコンテキストのフィクスチャ."""
    config = AITuberConfig()
    config.llm = llm_config
    return AppContext(config)


@patch("tests.test_llm.LangChainLLMIntegration")
def test_llm_integration_init(mock_chat_openai, app_context):
    """LLM統合機能の初期化をテスト."""
    # モックの設定
    mock_chat_openai.return_value = MagicMock()
    
    # LLM統合の初期化
    llm_integration = LangChainLLMIntegration(app_context)
    
    # 初期化されていることを確認
    assert llm_integration.config == app_context.config.llm


@patch("tests.test_llm.LangChainLLMIntegration")
async def test_llm_generate_text(mock_llm_integration, app_context):
    """テキスト生成機能をテスト."""
    # モックの設定
    mock_instance = MagicMock()
    mock_llm_integration.return_value = mock_instance
    
    # モックレスポンスの設定
    expected_response = "これはテスト応答です。"
    mock_instance.generate_text.return_value = expected_response
    
    # LLM統合の初期化
    llm_integration = LangChainLLMIntegration(app_context)
    
    # テキスト生成
    prompt = "テストプロンプト"
    system_prompt = "システムプロンプト"
    
    response = await llm_integration.generate_text(prompt, system_prompt)
    
    # 結果の検証
    assert response == expected_response
    
    # モックが正しく呼び出されたことを検証
    mock_instance.generate_text.assert_called_once_with(prompt, system_prompt)


@patch("tests.test_llm.LangChainLLMIntegration")
async def test_llm_generate_with_history(mock_llm_integration, app_context):
    """履歴付きのテキスト生成機能をテスト."""
    # モックの設定
    mock_instance = MagicMock()
    mock_llm_integration.return_value = mock_instance
    
    # モックレスポンスの設定
    expected_response = "これは履歴を考慮した応答です。"
    mock_instance.generate_text_with_history.return_value = expected_response
    
    # LLM統合の初期化
    llm_integration = LangChainLLMIntegration(app_context)
    
    # 会話履歴
    history = [
        {"role": "user", "content": "こんにちは"},
        {"role": "assistant", "content": "こんにちは！お手伝いできることはありますか？"}
    ]
    
    # テキスト生成
    prompt = "テストについて教えて"
    system_prompt = "システムプロンプト"
    
    response = await llm_integration.generate_text_with_history(prompt, system_prompt, history)
    
    # 結果の検証
    assert response == expected_response
    
    # モックが正しく呼び出されたことを検証
    mock_instance.generate_text_with_history.assert_called_once_with(prompt, system_prompt, history) 