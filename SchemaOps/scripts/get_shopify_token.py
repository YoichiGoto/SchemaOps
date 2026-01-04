#!/usr/bin/env python3
"""
Shopify簡易アクセストークン取得
Client IDとSecretを使用して直接アクセストークンを取得
"""
import requests
import json
from pathlib import Path

def get_shopify_access_token():
    """Shopifyアクセストークンを取得"""
    
    # 認証情報 (環境変数から読み込む、または設定ファイルから)
    import os
    client_id = os.environ.get("SHOPIFY_CLIENT_ID", "")
    client_secret = os.environ.get("SHOPIFY_CLIENT_SECRET", "")
    shop_domain = os.environ.get("SHOPIFY_SHOP_DOMAIN", "")
    
    # 環境変数が設定されていない場合は設定を促す
    if not all([client_id, client_secret, shop_domain]):
        print("⚠️  認証情報が環境変数に設定されていません")
        print("以下の環境変数を設定してください:")
        print("  export SHOPIFY_CLIENT_ID='your-client-id'")
        print("  export SHOPIFY_CLIENT_SECRET='your-client-secret'")
        print("  export SHOPIFY_SHOP_DOMAIN='your-shop.myshopify.com'")
        return
    
    print("=== Shopify アクセストークン取得 ===")
    print(f"Shop Domain: {shop_domain}")
    print(f"Client ID: {client_id}")
    print()
    
    # 方法1: プライベートアプリの作成を案内
    print("🔑 アクセストークンを取得する方法:")
    print()
    print("1. Shopify管理画面にアクセス:")
    print(f"   https://admin.shopify.com/store/{shop_domain}")
    print()
    print("2. Settings → Apps and sales channels")
    print("3. Develop apps → Create an app")
    print("4. App name: 'SchemaOps API Client'")
    print("5. Admin API access scopes を設定:")
    print("   - read_products")
    print("   - write_products")
    print("   - read_metafields")
    print("   - write_metafields")
    print()
    print("6. Configuration タブで Admin API access token をコピー")
    print("7. 形式: shpat_xxxxxxxxxxxxxxxxxxxxx")
    print()
    
    # 方法2: OAuth認証フロー
    print("🔄 または、OAuth認証フローを使用:")
    print("1. 以下のURLにアクセス:")
    oauth_url = f"https://{shop_domain}/admin/oauth/authorize?client_id={client_id}&scope=read_products,write_products,read_metafields,write_metafields&redirect_uri=https://your-domain.com/callback"
    print(f"   {oauth_url}")
    print()
    print("2. 認証後、リダイレクトURLから 'code' パラメータを取得")
    print("3. 以下のコマンドでアクセストークンを取得:")
    print("   python3 scripts/shopify_oauth.py")
    print()
    
    # 現在の認証情報でテスト
    print("🧪 現在の認証情報でテスト:")
    test_url = f"https://{shop_domain}/admin/api/2024-01/shop.json"
    
    # Client IDをAuthorizationヘッダーに設定してテスト
    headers = {
        "X-Shopify-Access-Token": client_id,  # 一時的にClient IDを使用
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(test_url, headers=headers)
        print(f"レスポンス: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 接続成功!")
            shop_data = response.json()
            print(f"Shop Name: {shop_data['shop']['name']}")
        else:
            print(f"❌ 接続失敗: {response.text}")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    print()
    print("📋 次のステップ:")
    print("1. 上記の方法でアクセストークンを取得")
    print("2. 環境変数を設定:")
    print("   export SHOPIFY_SHOP_DOMAIN='pioneerworktest1-2.myshopify.com'")
    print("   export SHOPIFY_ACCESS_TOKEN='shpat_xxxxxxxxxxxxxxxxxxxxx'")
    print("3. テスト実行:")
    print("   python3 scripts/shopify_api_tester.py")

if __name__ == "__main__":
    get_shopify_access_token()





