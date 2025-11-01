# Shopify Partner Account でのAPI連携設定ガイド

## 🛍️ Shopify Partner Account での設定手順

### 1. 開発ストアの作成

#### Partner Dashboard での操作
1. **Partner Dashboard** にログイン
2. **Apps** → **Create app** をクリック
3. **App type**: Custom app を選択
4. **App name**: `SchemaOps Integration` 等を入力
5. **App URL**: `https://your-domain.com` (開発時は `https://ngrok.io` 等)

#### 開発ストアの設定
```bash
# Shopify CLIを使用する場合
shopify app init
shopify app dev
```

### 2. Admin API アクセストークンの取得

#### プライベートアプリ作成
1. **開発ストア** → **Settings** → **Apps and sales channels**
2. **Develop apps** → **Create an app**
3. **App name**: `SchemaOps API Client`
4. **Admin API access scopes** を設定

#### 必要なスコープ設定
```json
{
  "scopes": [
    "read_products",
    "write_products", 
    "read_product_listings",
    "write_product_listings",
    "read_inventory",
    "write_inventory",
    "read_metafields",
    "write_metafields"
  ]
}
```

### 3. 認証情報の取得

#### アクセストークン取得
1. **Configuration** タブ
2. **Admin API access token** をコピー
3. **API secret key** をコピー

#### 設定例
```bash
# .envファイル
SHOPIFY_SHOP_DOMAIN=your-dev-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxxxxxxxxxxx
SHOPIFY_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
```

### 4. 接続テストの実行

#### テストスクリプト実行
```bash
# 環境変数設定
export SHOPIFY_SHOP_DOMAIN='your-dev-store.myshopify.com'
export SHOPIFY_ACCESS_TOKEN='shpat_xxxxxxxxxxxxxxxxxxxxx'

# テスト実行
python3 scripts/shopify_api_tester.py
```

#### 期待される結果
```
=== Shopify API 接続テスト開始 ===
✅ 接続成功: Your Dev Store
✅ 商品スキーマ取得成功: 9属性
✅ メタフィールド取得成功: 5件

=== テスト結果 ===
接続テスト: ✅ 成功
商品スキーマ: 9属性
メタフィールド: 5件
```

### 5. 実装コードの更新

#### 本番環境対応
- **requests ライブラリ**: 実際のAPI呼び出し
- **エラーハンドリング**: フォールバック機能
- **レート制限**: 2リクエスト/秒対応

#### スキーマ抽出
- **商品属性**: 実際の商品データから抽出
- **メタフィールド**: カスタム属性の取得
- **バリアント**: 商品バリエーション情報

### 6. セキュリティ設定

#### 推奨設定
- **HTTPS**: 必須
- **IP制限**: 可能な場合は設定
- **アクセストークン**: 定期的なローテーション

#### 環境変数管理
```bash
# 本番環境
export SHOPIFY_SHOP_DOMAIN='production-store.myshopify.com'
export SHOPIFY_ACCESS_TOKEN='shpat_production_token'

# 開発環境
export SHOPIFY_SHOP_DOMAIN='dev-store.myshopify.com'
export SHOPIFY_ACCESS_TOKEN='shpat_dev_token'
```

### 7. 監視・ログ設定

#### API利用状況監視
- **レート制限**: 2リクエスト/秒
- **エラー率**: 監視・アラート
- **レスポンス時間**: パフォーマンス監視

#### ログ設定
```python
# ログレベル設定
logging.basicConfig(level=logging.INFO)

# API呼び出しログ
logger.info(f"Shopify API call: {url}")
logger.info(f"Response: {response.status_code}")
```

### 8. トラブルシューティング

#### よくある問題
1. **401 Unauthorized**: アクセストークンの確認
2. **429 Too Many Requests**: レート制限の確認
3. **404 Not Found**: エンドポイントURLの確認

#### デバッグ方法
```bash
# 詳細ログ出力
export LOG_LEVEL=DEBUG
python3 scripts/shopify_api_tester.py

# 接続テストのみ
python3 -c "
from scripts.shopify_api_tester import ShopifyAPITester
tester = ShopifyAPITester('your-shop.myshopify.com', 'your-token')
print('接続テスト:', tester.test_connection())
"
```

### 9. 本番環境移行

#### 移行手順
1. **本番ストア**: 実際のShopifyストアでテスト
2. **スコープ確認**: 必要な権限の確認
3. **データバックアップ**: 既存データの保護
4. **段階的移行**: テスト→本番の順序

#### 本番環境設定
```bash
# 本番環境変数
export SHOPIFY_SHOP_DOMAIN='production-store.myshopify.com'
export SHOPIFY_ACCESS_TOKEN='shpat_production_token'
export ENVIRONMENT='production'
```

### 10. 継続運用

#### 定期メンテナンス
- **アクセストークン**: 定期的な更新
- **API仕様**: 変更の監視
- **パフォーマンス**: 最適化の実施

#### 監視ダッシュボード
- **API利用状況**: リアルタイム監視
- **エラー率**: アラート設定
- **レスポンス時間**: パフォーマンス追跡

## 🎯 次のステップ

### 即座に実行
1. **開発ストア作成**: Partner Dashboardで作成
2. **アクセストークン取得**: プライベートアプリ作成
3. **接続テスト**: `shopify_api_tester.py`実行

### 90日運用計画
- **M1 (30日)**: 本番環境移行
- **M2 (60日)**: 自動化・監視強化
- **M3 (90日)**: 最適化・拡張

**Shopify Partner Accountをお持ちの場合、上記手順で即座にAPI連携を開始できます。**





