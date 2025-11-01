<!-- 6c65ff29-8cea-4fd3-8d5f-7de04e0e5269 880576e8-ff86-4ec3-9013-b4645b797289 -->
# スキーマ資産オペレーション計画

## 目的・範囲

- 目的: ブランドのカタログデータが無くても、マーケットプレイスの公開仕様に基づき「共通スキーマ→MPマッピング→属性辞書→検証ルール→変更追従」を資産化。API未提供MPでも自動巡回・抽出・反映を高効率化。
- 初期スコープ（MP/カテゴリ）:
- MP: Google Merchant Center, Amazon, Shopify,（運用対象として）Rakuten, Yahoo Shopping, Mirakl, Mercari Shops
- カテゴリ: アパレル/スポーツ上位（サイズ・色・素材・バリエーション・画像要件中心）
- 期間: 準備4週＋運用90日

## チーム設計（パートタイム）

- 体制: オペレーター3–5名（各10–15h/週）, リード1名（10h/週）, 監修1名（3h/週）
- スキル: 日本語/英語の読解（公式ドキュメント）, スプレッドシート, ルール化の素養
- 担当: 収集/整形, マッピング, QA, 変更監視, ドキュメント管理

## リポジトリ/フォルダ構成（Google Drive想定）

- /SchemaOps
- /01_SOP
- /02_Templates
- Canonical_Schema（Google Sheets）
- MP_Mapping（Google Sheets）
- Attribute_Dictionary（Google Sheets）
- Validation_Checklist（Google Sheets）
- Change_Log（Google Sheets）
- Task_Tracker（Google Sheets）
- Sources_Registry（Google Sheets, 新規）
- Parser_Config（Google Sheets, 新規）
- /10_Working/{GMC,Amazon,Shopify,Rakuten,Yahoo,Mirakl,Mercari}
- /20_QA
- /30_Archive (versioned)
- /40_Reports (週次・月次KPI)

## スプレッドシート設計（テンプレの必須列）

- Canonical_Schema:
- attributeId, attributeName_ja, attributeName_en, definition, dataType, unitStandard(UCUM), allowedValues, requiredFlag, conditionalRule, examples, categoryPath(GPC/UNSPSC), notes, version
- MP_Mapping:
- mpName, categoryId/path, mpAttributeName, canonicalAttributeId, transformRule, regexRule, unitConversion, required, min/max/length, valueList, exampleIn, exampleOut, approvalNotes, lastVerifiedAt, sourceURL
- Attribute_Dictionary:
- attributeId, synonyms_ja, synonyms_en, prohibitedTerms, replacement, unitNormalization, imageRequirements, locale
- Validation_Checklist:
- SKU(TestId), attributeId, checkType(required/length/range/image/prohibited), passFail, failReason, autoFixRule, reviewer, checkedAt
- Change_Log:
- date, target(mp|retailer), name, changeSummary, impactedAttributes, severity(critical/major/minor), SLA_hours, ETA, status(new/triaged/in-progress/updated/verified/closed), owner, lastVerifiedAt, docURL, sourceURL, notes
- Task_Tracker:
- taskId, task, owner, due, status, notes, evidenceURL
- Sources_Registry（新規）:
- name, type(html/pdf/xlsx), url, requiresLogin(yes/no), checkFrequency(daily/weekly), snapshotPolicy, parserProfile, owner, lastCheckedAt
- Parser_Config（新規）:
- parserProfile, docType, selectors_or_prompts, jsonSchemaURL, examplesURL, confidenceThreshold, fallbackRule

## SOP（運用手順の骨子）

- 収集: 公式仕様/ヘルプ/APIを一次情報として保存（sourceURL必須）
- 設計: 共通スキーマ→MP差分を明確化（required/条件付き必須/推奨）
- マッピング: Canonical→MP_Mappingを属性単位に定義（transformRuleは関数/正規表現で表現）
- QA: Validation_Checklistで合成SKU100件をPASS ≥90%まで反復
- 変更追従: 週次で各MPを巡回、Change_Logへ記録→影響範囲→テンプレ更新→QA再実施（目標MTTR ≤72h/重大）
- 版管理: 変更はテンプレをコピーしversion列更新、差分ハイライト必須

## 非API向け 自動巡回・抽出・反映アーキテクチャ（Google/Shopify/Rakuten/Yahoo/Mercari 等）

- レベル0（即時運用）: ページ監視サービス（Distill.io/VisualPing）＋メール→GASでChange_Logへ自動登録、添付xlsxはDrive保存。
- レベル1（自社巡回）: ヘッドレスブラウザ（Playwright）でSources_Registryに従いHTML/PDF/xlsxを取得→スナップショット保存（/30_Archive）。robots遵守・レート制御。
- レベル2（差分検知）: 正規化（HTML→テキスト/表、PDF→テキスト/表、xlsx→ヘッダ/制約）→前版と差分ハッシュ・行単位diff→changeSummary生成。
- レベル3（AI抽出）: LLMにプロンプト/few-shotで「属性名/必須/型/長さ/選択肢/有効日」をJSONへ抽出（Parser_Configでプロファイル管理）。信頼度<閾値は要レビュー。
- レベル4（自動提案）: MP_Mapping/Attribute_Dictionaryへの「提案変更」を作成→承認シートで人間承認→承認後にversion更新とQA実行。
- レベル5（通知/監査）: Lark通知（重大=即時, それ以外=日次まとめ）、Change_LogのSLA_hoursに基づきリマインド。全スナップショットと承認履歴を保存。

## Excel指定フォーマット（小売）への特化

- 取り込み: 新しいフォーマットexcelを受け取ったら指定のフォルダに保管→ファイル名 Retailer/YYYYMMDD/spec_vX.xlsx。（ファイル名自動変更）Sources_Registryに登録。
- 差分: 旧版とのxlsx構造diff（列名/必須/長さ/選択肢）を自動抽出、変更種別（追加/削除/必須化/型変更）を分類。
- 反映: Canonical/Mappingの該当セルへ提案変更を作成→承認後反映→Validationで合成SKUチェック。
- リリース: リリースノート（変更点/影響/適用日）を自動生成して配布。

## KPI（週次→月次レポート）

- カバレッジ: 重点カテゴリ×MPの必須属性網羅率 ≥90%
- 自動マッピング定義率: transformRule定義済み属性比率 ≥85%
- Validation PASS率（合成SKU）: ≥90%（主要属性）
- 変更追従MTTR（重大）: ≤72時間
- 検知リードタイム: 主要ソースの変更検知までの中央値 ≤24h
- 抽出精度（AI）: precision ≥95%, recall ≥90%
- 自動承認率: 人手介入不要で反映できた提案の割合 ≥60%

## 4週間セットアップ計画

- W1: フォルダ/テンプレ配備、GMC仕様収集→Canonical初版、Sources_Registry作成
- W2: Amazon/Shopify差分反映→MP_Mapping初版、Attribute_Dictionary初版、メール→Drive自動化（GAS）
- W3: xlsx差分抽出スクリプト・AI抽出プロンプトのたたき台、合成SKU100件でQA→改善
- W4: Lark通知/承認シート/レポート雛形、変更監視SOP確定→運用開始

## 90日運用マイルストーン

- M1(30日): カバレッジ70%/定義率70%/PASS80%/検知≤48h
- M2(60日): カバレッジ85%/定義率80%/PASS88%/検知≤36h/AI precision≥93%
- M3(90日): カバレッジ90%/定義率85%/PASS90%/MTTR≤72h/検知≤24h/AI precision≥95%

## リスクと対策

- アクセス制限・改版頻度: ソース多重化＋スナップショット保存＋週次レビュー会
- AI抽出の揺らぎ: few-shot増強・ルールベース併用・閾値運用でHITL
- セキュリティ/法令: robots遵守・認証情報は共有Drive機密区画、監査ログ保全

## To-dos（実装）

- setup-folders: Google DriveにSchemaOpsフォルダ構成を作成
- create-templates: 各テンプレ（8種）をスプレッドシートで作成（新規2種含む）
- write-sop: 収集/設計/マッピング/QA/変更追従/HITL承認のSOP作成
- recruit-ops: パートタイム運用者3–5名の募集・選定
- onboard-training: SOP/テンプレに基づく導入トレーニング実施
- build-initial-schemas: GMC中心にCanonical/MPマッピング初版作成
- qa-pilot: 合成SKU100件でValidation PASS≥90%達成
- change-monitoring: GASメール取込・Slack通知・Change_Log運用開始（MTTR目標設定）
- excel-diff: xlsx差分抽出スクリプト（列/必須/長さ/選択肢）
- ai-extractor: 仕様→JSON抽出のLLMプロンプト/評価指標（precision/recall）
- approvals: 承認シートと自動反映フロー（提案→承認→反映→バージョン）
- reporting: 週次・月次KPIレポート雛形で定例運用

### To-dos

- [x] Google DriveにSchemaOpsフォルダ構成を作成
- [x] 各テンプレ（6種）をスプレッドシートで作成
- [x] 収集/設計/マッピング/QA/変更追従のSOP作成
- [x] パートタイム運用者3–5名の募集・選定
- [x] SOP/テンプレに基づく導入トレーニング実施
- [x] GMC中心にCanonical/MPマッピング初版作成
- [x] 合成SKU100件でValidation PASS≥90%達成
- [x] 変更監視とChange_Log運用開始（MTTR目標設定）
- [x] 週次・月次KPIレポート雛形で定例運用



