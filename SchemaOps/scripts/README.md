# SchemaOps Scripts

## excel_diff.py
- CSV化した旧新テンプレを比較し、列の追加/削除/名称変更、必須/長さ/選択肢の変更を抽出
- 使い方: `python excel_diff.py old.csv new.csv > diff.md`

## export_json.py
- Canonical_Schema.csv / MP_Mapping.csv を正規化JSONに変換し /30_Archive に出力
- 使い方: `python export_json.py --input-dir ../02_Templates --out ../30_Archive/$(date +%Y%m%d)`

## generate_release_notes.py
- Change_Log.csv からリリースノート(Markdown)を生成
- 使い方: `python generate_release_notes.py ../02_Templates/Change_Log.csv > release_notes.md`

## gas/change_log_ingest.gs（サンプル）
- Gmailのラベルからメールを読み、Change_Logシートに行追加（ETA/ownerは手入力）

