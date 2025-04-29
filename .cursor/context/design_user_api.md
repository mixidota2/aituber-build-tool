# エンドユーザー向け対話API設計（design_user_api.md）

## 1. 目的
AIキャラクターとのチャット・音声対話など、エンドユーザーが直接利用するAPIの設計方針をまとめる。

## 2. 主なAPIエンドポイント例

### 2.1 チャットAPI
- `POST /api/chat`
  - 入力: `character_id`, `text`, `context`（省略可）
  - 出力: `response_text`, `session_id`, `metadata`

### 2.2 音声対話API
- `POST /api/voice_chat`
  - 入力: `character_id`, `audio_data`, `context`（省略可）
  - 出力: `response_text`, `response_audio`, `session_id`, `metadata`

## 3. 設計方針
- キャラクターごとに対話セッションを分離
- テキスト・音声どちらもサポート
- 応答速度最適化（ストリーミング/非同期対応）
- セッション管理（session_idによる継続対話）
- 必要に応じてユーザー認証も拡張可能

## 4. 補足
- LLM対話エンジン、音声認識・合成（STT/TTS）と連携
- 応答メタデータ（信頼度、参照ナレッジ等）も返却可能
- 将来的なLive2D/3D連携やマルチモーダル拡張も考慮 