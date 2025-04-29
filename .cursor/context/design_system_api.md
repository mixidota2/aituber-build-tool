# システム連携・運用者向けAPI設計（design_system_api.md）

## 1. 目的
AIキャラクターのナレッジ追加・管理、キャラクター設定管理など、運用者や外部システムが利用するAPIの設計方針をまとめる。

## 2. 主なAPIエンドポイント例

### 2.1 ナレッジ管理API
- `POST /api/knowledge/add`
  - 入力: `character_id`, `source_type`（text/pdf/web/notion等）, `content`（テキスト/ファイル/URL/NotionページID等）, `metadata`（任意）
  - 出力: `knowledge_id`, `status`, `message`
- `DELETE /api/knowledge/remove`
  - 入力: `character_id`, `knowledge_id`
  - 出力: `status`, `message`
- `GET /api/knowledge/list`
  - 入力: `character_id`
  - 出力: `knowledge_list`

### 2.2 キャラクター設定管理API
- `PUT /api/character/update`
  - 入力: `character_id`, `settings`（プロンプト、プロファイル等）
  - 出力: `status`, `message`
- `POST /api/character/switch`
  - 入力: `character_id`
  - 出力: `status`, `message`

## 3. 設計方針
- キャラクターごとにリソース（ナレッジ・設定等）を分離管理
- 多様なナレッジソース（テキスト、PDF、Web、Notion等）に対応
- メタデータ（出典、日付、タグ等）付与に対応
- ベクトルDBやRDB等、適切なストレージに保存
- API認証・認可（トークン/キー方式）
- 拡張性（新リソース種別やキャラクター追加が容易）

## 4. 補足
- Notion等外部API連携用トークンの安全な管理
- 設定ファイルや管理UIとの連携も将来的に拡張可能
- ナレッジの自動更新・監視機能も設計段階で考慮 