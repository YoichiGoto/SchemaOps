# SchemaOps SOP

## 1. 目的
- 各MP/小売仕様の変更を迅速かつ高品質に反映し、承認率・Time-to-Listingを最大化する

## 2. 体制・権限
- 役割: Sources / Canonical / Mapping / QA / Change-Release
- 権限: テンプレ編集権限は担当者＋レビュー担当に限定

## 3. 日次運用
- 監視通知の確認→Change_Log起票（4時間以内）
- 軽微変更の反映→Validation 10SKU
- 未解決FAILの棚卸し

## 4. 週次運用
- 変更レビュー会（critical/majorのETA見直し）
- KPI更新（PASS率・MTTR・検知リードタイム）
- バージョン確定とアーカイブ

## 5. 手順
- 収集: Sources_Registryに登録、スナップショット保存
- 設計: Canonical_Schema更新、辞書更新
- マッピング: MP_Mapping更新（transform/regex/unit）＋例値
- 検証: Validation_ChecklistでPASS≥90%まで反復
- 変更追従: Change_Log管理（status遷移、SLA遵守）
- リリース: リリースノート配布、適用日設定

## 6. 重大度基準
- critical: 必須項目の追加/必須化、提出不可
- major: 大幅な属性追加/名称変更/選択肢変更
- minor: 任意項目や説明の更新

## 7. KPI目標
- PASS≥90%、MTTR≤72h、検知≤24h、自動承認≥60%

## 8. 監査
- sourceURL/lastVerifiedAt必須
- 承認履歴とスナップショットを/30_Archiveに保存
