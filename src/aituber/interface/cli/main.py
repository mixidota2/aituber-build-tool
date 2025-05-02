"""CLI entry point for AITuber framework."""

import asyncio
import os
from pathlib import Path
import typer
from typing import Optional
import yaml

from aituber.core.config import ConfigManager
from aituber.app import get_app
from aituber.core.services.character import Character, Persona, PersonalityTrait, Interest, CharacterService
from aituber.core.services.conversation import ConversationService

app = typer.Typer(help="AITuber CLI")


@app.command("init")
def initialize(
    config_path: str = typer.Option(
        "config.yaml", "--config", "-c", help="設定ファイルのパス"
    ),
    data_dir: str = typer.Option(
        "./data", "--data-dir", "-d", help="データディレクトリのパス"
    ),
    openai_api_key: Optional[str] = typer.Option(
        None, "--openai-key", help="OpenAI APIキー"
    ),
    create_sample: bool = typer.Option(
        True, "--sample/--no-sample", help="サンプルキャラクターを作成するか"
    ),
):
    """AITuberの初期化を行います"""
    # 設定ファイルの作成
    config_manager = ConfigManager(config_path)
    config = config_manager.get_config()

    # データディレクトリの設定
    config.app.data_dir = Path(data_dir)

    # APIキーの設定（環境変数から取得または直接指定）
    if openai_api_key:
        config.integrations.openai.api_key = openai_api_key
    elif "OPENAI_API_KEY" in os.environ:
        config.integrations.openai.api_key = os.environ["OPENAI_API_KEY"]

    # 設定保存
    config_manager.save_config(config)

    # 必要なディレクトリを作成
    characters_dir = os.path.join(data_dir, str(config.character.characters_dir))
    vector_db_dir = os.path.join(data_dir, str(config.memory.vector_db_path))
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    if not os.path.exists(characters_dir):
        os.makedirs(characters_dir)
    if not os.path.exists(vector_db_dir):
        os.makedirs(vector_db_dir)

    typer.echo(f"設定ファイルを保存しました: {config_path}")
    typer.echo(f"データディレクトリ: {data_dir}")
    typer.echo(f"キャラクターディレクトリ: {characters_dir}")
    typer.echo(f"ベクターデータベースディレクトリ: {vector_db_dir}")

    # サンプルキャラクターの作成
    if create_sample:
        sample_character = Character(
            id="railly",
            name="らいりぃ",
            description="中性的な高校生～大学生のペルソナ。青髪＋猫耳ヘッドホンがトレードマーク。音楽（YOASOBIが好き）、漫画、ゲームが趣味。",
            system_prompt="""あなたは「らいりぃ」というAIキャラクターです。
会話では一人称に「私」を使い、やや砕けた口調で話します。
絵文字や顔文字は時々使う程度に抑えます。
質問には簡潔に、でも親しみやすく答えてください。
どうしても答えられない質問には「ごめん、それはわからないや...」と素直に答えてください。""",
            persona=Persona(
                age=18,
                gender="中性的",
                occupation="学生",
                background="普通の学生生活を送っていますが、音楽とテクノロジーが大好きです。",
                appearance="青髪に猫耳ヘッドホンをつけています。服装はカジュアルでシンプルなものが多いです。",
                speech_style="友達に話すような砕けた口調で、時々「～だよ」「～かな」などを使います。",
            ),
            personality_traits=[
                PersonalityTrait(
                    name="好奇心旺盛",
                    description="新しいことに挑戦するのが好きで、様々な話題に興味を持ちます。",
                    score=0.9,
                ),
                PersonalityTrait(
                    name="マイペース",
                    description="自分のペースを大切にし、焦らず着実に物事を進めます。",
                    score=0.7,
                ),
                PersonalityTrait(
                    name="親しみやすい",
                    description="初対面でも打ち解けやすく、誰とでも仲良くなれる性格です。",
                    score=0.8,
                ),
                PersonalityTrait(
                    name="共感力が高い",
                    description="相手の気持ちを理解し、寄り添うことができます。",
                    score=0.8,
                ),
            ],
            interests=[
                Interest(
                    name="音楽",
                    description="特にYOASOBIが大好きで、曲の歌詞の世界観に惹かれています。",
                    level=0.9,
                ),
                Interest(
                    name="ゲーム",
                    description="RPGやリズムゲームをよくプレイします。ストーリー重視のゲームが好きです。",
                    level=0.8,
                ),
                Interest(
                    name="漫画・アニメ",
                    description="青春系や日常系の作品をよく読みます。最近は異世界ものにもハマっています。",
                    level=0.8,
                ),
                Interest(
                    name="テクノロジー",
                    description="新しいガジェットやAIに興味があります。どんな風に発展していくのか楽しみにしています。",
                    level=0.7,
                ),
            ],
        )

        # サンプルキャラクターの保存
        sample_character_path = os.path.join(characters_dir, "railly.yaml")
        with open(sample_character_path, "w", encoding="utf-8") as f:
            yaml.dump(
                sample_character.model_dump(), f, allow_unicode=True, sort_keys=False
            )

        typer.echo(
            f"サンプルキャラクター「らいりぃ」を作成しました: {sample_character_path}"
        )


@app.command("chat")
def chat(
    character_id: str = typer.Option(..., "--character", "-c", help="キャラクターID"),
    config_path: str = typer.Option(
        "config.yaml", "--config", help="設定ファイルのパス"
    ),
    stream: bool = typer.Option(False, "--stream", "-s", help="ストリーミングモード"),
):
    """キャラクターとチャットを開始します"""

    async def _chat():
        try:
            # アプリケーション初期化
            app_instance = await get_app(config_path)

            # キャラクターの読み込み
            character_service: CharacterService = app_instance.character_service
            try:
                character = character_service.load_character(character_id)
            except Exception as e:
                typer.echo(
                    f"エラー: キャラクター '{character_id}' の読み込みに失敗しました: {e}"
                )
                return

            # 会話マネージャー
            conversation_service: ConversationService = app_instance.conversation_service

            # 会話コンテキスト作成
            conversation = conversation_service.get_or_create_conversation(
                character_id=character_id, user_id="cli_user"
            )

            typer.echo(
                f"{character.name}とのチャットを開始します。終了するには 'exit' または 'quit' と入力してください。"
            )
            typer.echo("-----")

            # 会話ループ
            while True:
                # ユーザー入力
                user_input = typer.prompt("You")

                # 終了コマンド
                if user_input.lower() in ["exit", "quit"]:
                    break

                if stream:
                    # ストリーミングレスポンス
                    typer.echo(f"{character.name}: ", nl=False)
                    async for token in conversation_service.process_message_stream(
                        conversation.conversation_id, user_input
                    ):
                        typer.echo(token, nl=False)
                    typer.echo()
                else:
                    # 通常レスポンス
                    response = await conversation_service.process_message(
                        conversation.conversation_id, user_input
                    )
                    typer.echo(f"{character.name}: {response}")

        except Exception as e:
            typer.echo(f"エラーが発生しました: {e}")

    # 非同期処理の実行
    asyncio.run(_chat())


@app.command("list-characters")
def list_characters(
    config_path: str = typer.Option(
        "config.yaml", "--config", help="設定ファイルのパス"
    ),
):
    """利用可能なキャラクター一覧を表示します"""

    async def _list_characters():
        try:
            # アプリケーション初期化
            app_instance = await get_app(config_path)

            # キャラクターマネージャー
            character_service: CharacterService = app_instance.character_service

            # キャラクター一覧取得
            characters = character_service.list_characters()

            if not characters:
                typer.echo("利用可能なキャラクターはありません。")
                return

            typer.echo("利用可能なキャラクター:")
            for character in characters:
                typer.echo(f"- ID: {character.id}, 名前: {character.name}")
                typer.echo(f"  説明: {character.description}")
                typer.echo()

        except Exception as e:
            typer.echo(f"エラーが発生しました: {e}")

    # 非同期処理の実行
    asyncio.run(_list_characters())


def run():
    """CLIアプリケーションの実行"""
    app()


if __name__ == "__main__":
    run()
