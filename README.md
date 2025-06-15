# AITuber Framework

任意のキャラクター設定を適用できる汎用AITuberフレームワーク。
めちゃめちゃWIP。

## 機能概要

- チャットおよび音声での対話
- セッションを超えた長期的なコンテキスト保持
- 任意のキャラクター設定の適用と切り替え機能
- キャラクター設定の管理システム
- OpenAI APIを活用したLLM連携
- ストリーミング応答によるリアルタイムな対話
- ChromaDBを使用したベクトル記憶管理

## インストール方法

```bash
# uvを使用してインストール
uv sync --all-groups -no-dev 

# 開発に必要な依存関係も含めてインストール
uv sync --all-groups
```

インストールすると `aituber` コマンドが利用可能になります。

## 使い方

### 初期設定

初めに設定ファイルを作成します。初期化時にサンプルキャラクター「らいりぃ」が自動的に作成されます。

```bash
# 基本的な初期化
aituber init

# データディレクトリの指定
aituber init --data-dir ./data

# サンプルキャラクターを作成せずに初期化
aituber init --no-sample
```

APIキーの設定：

```bash
export OPENAI_API_KEY=your_api_key_here
```

### キャラクター設定

キャラクター設定はYAMLファイルで管理されます。以下は基本的な設定例です：

```yaml
id: example_character
name: キャラクター名前
version: 1.0.0
description: キャラクターの説明文
system_prompt: |
  このキャラクターのシステムプロンプト。
  複数行で記述可能です。
persona:
  age: 20
  gender: 設定性別
  occupation: 職業
  background: 経歴や背景設定
  appearance: 外見の特徴
  speech_style: 話し方の特徴
personality_traits:
  - name: 性格特性1
    description: 性格特性の説明
    score: 0.8
interests:
  - name: 興味1
    description: 興味の説明
    level: 0.9
voicevox:
  style_id: 1  # VOICEVOXのスタイルID（オプション）
```

ファイルを `data/characters/` ディレクトリに配置してください。

### キャラクター一覧

登録されているキャラクター一覧を表示します。

```bash
aituber list-characters
```

### チャット開始

キャラクターとチャットを開始します。

```bash
# 通常モード
aituber chat --character railly

# ストリーミングモード（リアルタイムな応答）
aituber chat --character railly --stream
```

### APIサーバーの起動

FastAPIを使ったWebAPIサーバーを起動できます。テキスト対話と音声対話の両方に対応しています。

```bash
# デフォルト設定でサーバー起動（ホスト: 127.0.0.1, ポート: 8000）
uv run aituber serve

# ホストとポートを指定
uv run aituber serve --host 127.0.0.1 --port 8000

# 開発モード（ファイル変更時の自動リロード）
uv run aituber serve --reload
```

サーバー起動後、以下のURLにアクセスできます：

- **APIドキュメント**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

### API使用例

#### テキスト対話

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "railly",
    "user_id": "test_user", 
    "message": "こんにちは！",
    "response_type": "text"
  }'
```

#### テキスト入力→音声出力

```bash
# 専用エンドポイント
curl -X POST http://127.0.0.1:8000/chat/text-to-speech \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "railly",
    "user_id": "test_user",
    "message": "音声で返事して！"
  }' \
  --output response.wav

# 通常のチャットAPIでも可能
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "railly",
    "user_id": "test_user",
    "message": "音声で返事してください",
    "response_type": "audio"
  }' \
  --output chat_audio.wav
```

#### その他のAPI

```bash
# キャラクター一覧
curl http://127.0.0.1:8000/characters

# ストリーミング対話
curl -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "railly",
    "user_id": "test_user",
    "message": "ストリーミングで返答して"
  }'

# 会話履歴
curl http://127.0.0.1:8000/conversations/{conversation_id}/history
```

### 会話の継続

APIでは`conversation_id`を使用して会話の継続が可能です：

```bash
# 初回メッセージ（新しい会話IDが生成される）
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "railly",
    "user_id": "test_user",
    "message": "初回メッセージです",
    "response_type": "text"
  }'

# 返答から conversation_id を取得し、続きの会話
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "railly",
    "user_id": "test_user",
    "conversation_id": "取得したconversation_id",
    "message": "続きのメッセージです",
    "response_type": "text"
  }'
```

### トラブルシューティング

**キャラクターが見つからない場合:**

1. 初期化が完了していることを確認:
   ```bash
   uv run aituber init
   ```

2. キャラクターファイルの存在確認:
   ```bash
   ls -la data/characters/
   ```

3. デバッグエンドポイントで詳細確認:
   ```bash
   curl http://127.0.0.1:8000/debug/character-dir
   ```

## 開発者向け情報

### 基本的な検証手順

uvを使ってインストールしていない場合は、以下のコマンドで直接実行することもできます：

```bash
# モジュールとして直接実行
uv run python -m aituber init
uv run python -m aituber list-characters
uv run python -m aituber chat --character railly
```

検証の基本手順：

1. 初期化を実行（サンプルキャラクターも自動作成されます）
   ```bash
   aituber init
   ```

2. キャラクター一覧を確認
   ```bash
   aituber list-characters
   ```

3. チャット機能をテスト
   ```bash
   aituber chat --character railly
   ```

### テスト

このプロジェクトには包括的なテストスイートが含まれています：

#### テスト構造

```
tests/
├── unit/          # 単体テスト（モックを使用）
│   ├── api/       # API エンドポイントのテスト
│   ├── test_character.py
│   ├── test_conversation_manager.py
│   └── test_services.py
└── integration/   # 統合テスト（実際のAPIサーバーを使用）
    └── test_api_integration.py
```

#### テスト実行

```bash
# 全テスト実行
uv run pytest tests/

# 単体テストのみ
uv run pytest tests/unit/

# 統合テストのみ（実際のAPIサーバーを起動してテスト）
uv run pytest tests/integration/

# 詳細出力
uv run pytest tests/ -v

# 特定のテストファイル
uv run pytest tests/unit/test_services.py

# 特定のテスト関数
uv run pytest tests/unit/test_services.py::test_llm_generate
```

#### 統合テストについて

統合テストは実際のAPIサーバーを自動起動・停止してテストを実行します：

- **自動サーバー管理**: テスト実行時に自動でAPIサーバーが起動・停止されます
- **一時的な設定**: テスト用の一時設定ファイルとデータディレクトリを使用
- **OpenAI API**: `OPENAI_API_KEY`環境変数が設定されていない場合、LLMが必要なテストは自動的にスキップされます

```bash
# OpenAI APIキーを設定して全機能をテスト
export OPENAI_API_KEY=your_api_key_here
uv run pytest tests/integration/
```

#### コード品質チェック

開発時は以下のコマンドでコード品質をチェックしてください：

```bash
# コードの整形とリンティング
uv run ruff check src/
uv run ruff check --fix src/

# 型チェック
uv run mypy src/aituber/

# 全チェック（テスト + リント + 型チェック）
uv run pytest tests/ && uv run ruff check src/ && uv run mypy src/aituber/
```

## アーキテクチャ

```
                                [キャラクター設定マネージャ]
                                           ↓
[入力(テキスト/音声)] → [前処理] → [OpenAI LLM] → [後処理] → [出力(テキスト/音声)]
                |              ↑          ↑           ↓
                |         [長期記憶DB] [知識ベース] [記憶保存]
                ↓              ↑          ↑           ↓
         [音声認識(STT)]        └──────[統合モジュール]─────┘
```

### コア構成要素

- **ServiceContainer**: 依存性注入コンテナとしての役割を果たし、各サービスのシングルトンインスタンスを管理
- **CharacterService**: キャラクター設定の管理を担当
- **ConversationService**: 会話の処理と記憶の管理を担当
- **OpenAIService**: OpenAI APIとの通信を抽象化
- **ChromaDBMemoryService**: 会話コンテキストの長期記憶をベクトルDBで管理

### 拡張性

このフレームワークは拡張性を重視して設計されています：

- 各サービスは明確なインターフェースを持ち、容易に置き換え可能
- 新しいキャラクターは設定ファイルを追加するだけで利用可能
- 将来的にはWeb API、音声認識、Live2D/3Dモデルなどの統合も計画
