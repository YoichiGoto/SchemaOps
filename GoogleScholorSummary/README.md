# Google Scholar Research Automation

指定されたキーワードや著者の新着論文をGoogle Scholarから検索し、PDFをダウンロードしてGeminiで要約、Larkに通知する自動化ツールです。

## セットアップ

1. **要件**
   - GitHubアカウント
   - SerpApi アカウント & APIキー
   - Google Cloud (Gemini) APIキー
   - Lark (Feishu) アプリ (App ID, App Secret)

2. **GitHub Secretsの設定**
   リポジトリの `Settings` > `Secrets and variables` > `Actions` に以下のSecretを追加してください。

   - `SERPAPI_KEY`: SerpApiのAPIキー
   - `GEMINI_API_KEY`: Google GeminiのAPIキー
   - `Lark_APP_ID`: Larkアプリの App ID
   - `Lark_APP_SECRET`: Larkアプリの App Secret
   - `Lark_CHAT_ID`: 通知先のLarkグループ（またはユーザー）のChat ID

   > **Chat IDの取得方法**: Larkの開発者ツールや、API Explorerなどで確認できます。または、Botをグループに追加し、グループの設定からIDを確認できる場合があります。

3. **検索対象の設定**
   `config/targets.json` を編集して、検索したいキーワードや著者を設定してください。

   ```json
   {
     "keywords": ["keyword1", "keyword2"],
     "authors": ["Author Name"]
   }
   ```

## 動作

- 毎週月曜日 午前9時 (JST) に自動実行されます。
- PDFファイルは `data/pdfs/` に保存されます。
- 処理済み論文は `data/history.json` に記録され、次回以降はスキップされます。
