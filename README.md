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
interests:
  - name: 興味1
    description: 興味の説明
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

## 開発者向け検証手順

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
