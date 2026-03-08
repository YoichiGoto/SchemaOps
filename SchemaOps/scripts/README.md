# SchemaOps Scripts

## TRAM 準拠パイプライン

### policy_crawler.py
- Sources_Registry の URL をクロールし、HTML/PDF/xlsx を 30_Archive/{mp}/{date}/ にスナップショット保存
- 変更検知時に change_monitor へ determination_needs_review を報告
- 使い方: `python policy_crawler.py`

### document_chunker.py
- 規約・ポリシー文書をセマンティック分割（ルールベース＋LLM フォールバック）
- メタデータ付与: parentDoc, marketplace, effectiveDate, policyType, hierarchy
- 使い方: `python document_chunker.py <file> <marketplace> <output.json> [policyType]`

### indexer.py
- チャンクを Dense (ChromaDB) + Sparse (キーワード) でハイブリッドインデックス
- 使い方: `python indexer.py <chunks.json> <index_dir> [--reset]`

### retriever.py
- タスク＋商品カテゴリ＋MP でハイブリッド検索、マージ、隣接拡張
- 使い方: `python retriever.py <index_dir> "<query>" <marketplace> [--no-expand]`

### determination_engine.py
- リスト可否・制限・表示義務の構造化提案＋理由＋引用を出力
- 使い方: `python determination_engine.py <sections.json> <task> <category> <marketplace> [feedback_path]`

---

## 既存スクリプト

## excel_diff.py
- CSV化した旧新テンプレを比較し、列の追加/削除/名称変更、必須/長さ/選択肢の変更を抽出
- 使い方: `python excel_diff.py old.csv new.csv > diff.md`

## export_json.py
- Canonical_Schema.csv / MP_Mapping.csv を正規化JSONに変換し /30_Archive に出力
- `--determinations <path>` で承認済み determination を rules/{mp}/{category}/v{date}.json に出力
- 使い方: `python export_json.py --input-dir ../02_Templates --out ../30_Archive/$(date +%Y%m%d) [--determinations approved.json]`

## change_monitor.py
- スキーマ変更＋生ドキュメント変更を監視。document_updated 時に determination_needs_review フラグ
- get_determination_review_alerts() で要更新アラート取得

## approval_workflow.py
- 修正・却下時に correction_reason 必須。feedback_store.json に保存
- get_determination_review_alerts() で change_monitor のアラート取得

## validate_skus.py
- `--rules <dir>` で determination ルールを読み込み、listable/restrictions チェック追加

## generate_release_notes.py
- Change_Log.csv からリリースノート(Markdown)を生成
- 使い方: `python generate_release_notes.py ../02_Templates/Change_Log.csv > release_notes.md`

## gas/change_log_ingest.gs（サンプル）
- Gmailのラベルからメールを読み、Change_Logシートに行追加（ETA/ownerは手入力）

