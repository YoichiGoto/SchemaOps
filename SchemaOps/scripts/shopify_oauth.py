#!/usr/bin/env python3
"""
Shopify OAuth認証フロー実装
Client IDとSecretを使用してAccess Tokenを取得
"""
import os
import json
import requests
from urllib.parse import urlencode, parse_qs
import webbrowser
from typing import Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ShopifyOAuth:
    """Shopify OAuth認証クラス"""
    
    def __init__(self, client_id: str, client_secret: str, shop_domain: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.shop_domain = shop_domain
        self.redirect_uri = "https://your-domain.com/oauth/callback"  # 実際のドメインに変更
        self.scopes = [
            "read_products",
            "write_products",
            "read_metafields",
            "write_metafields",
            "read_inventory",
            "write_inventory"
        ]
    
    def get_authorization_url(self) -> str:
        """認証URLを生成"""
        params = {
            "client_id": self.client_id,
            "scope": ",".join(self.scopes),
            "redirect_uri": self.redirect_uri,
            "state": "random_state_string"  # CSRF対策
        }
        
        auth_url = f"https://{self.shop_domain}/admin/oauth/authorize?" + urlencode(params)
        return auth_url
    
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """認証コードをアクセストークンに交換"""
        url = f"https://{self.shop_domain}/admin/oauth/access_token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code
        }
        
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            token_data = response.json()
            logger.info("✅ アクセストークン取得成功")
            return token_data
        else:
            logger.error(f"❌ トークン取得失敗: {response.status_code} - {response.text}")
            return {}
    
    def test_access_token(self, access_token: str) -> bool:
        """アクセストークンのテスト"""
        url = f"https://{self.shop_domain}/admin/api/2024-01/shop.json"
        headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            shop_data = response.json()
            logger.info(f"✅ 接続成功: {shop_data['shop']['name']}")
            return True
        else:
            logger.error(f"❌ 接続失敗: {response.status_code} - {response.text}")
            return False

def main():
    """メイン実行関数"""
    # 認証情報 (環境変数から読み込む)
    import os
    client_id = os.environ.get("SHOPIFY_CLIENT_ID", "")
    client_secret = os.environ.get("SHOPIFY_CLIENT_SECRET", "")
    shop_domain = os.environ.get("SHOPIFY_SHOP_DOMAIN", "")
    
    # 環境変数が設定されていない場合はエラー
    if not all([client_id, client_secret, shop_domain]):
        print("⚠️  エラー: 認証情報が環境変数に設定されていません")
        print("以下の環境変数を設定してください:")
        print("  export SHOPIFY_CLIENT_ID='your-client-id'")
        print("  export SHOPIFY_CLIENT_SECRET='your-client-secret'")
        print("  export SHOPIFY_SHOP_DOMAIN='your-shop.myshopify.com'")
        return
    
    # OAuth認証フロー開始
    oauth = ShopifyOAuth(client_id, client_secret, shop_domain)
    
    print("=== Shopify OAuth認証フロー ===")
    print(f"Shop Domain: {shop_domain}")
    print(f"Client ID: {client_id}")
    print()
    
    # 1. 認証URL生成
    auth_url = oauth.get_authorization_url()
    print("1. 以下のURLにアクセスしてアプリを認証してください:")
    print(f"   {auth_url}")
    print()
    
    # 2. 認証コードの入力待ち
    print("2. 認証後、リダイレクトURLから 'code' パラメータを取得してください")
    print("   例: https://your-domain.com/oauth/callback?code=xxxxxxxx&state=...")
    print()
    
    code = input("認証コードを入力してください: ").strip()
    
    if code:
        # 3. アクセストークン取得
        print("\n3. アクセストークンを取得中...")
        token_data = oauth.exchange_code_for_token(code)
        
        if token_data and "access_token" in token_data:
            access_token = token_data["access_token"]
            print(f"✅ アクセストークン: {access_token}")
            
            # 4. 接続テスト
            print("\n4. 接続テスト実行中...")
            if oauth.test_access_token(access_token):
                print("✅ OAuth認証完了!")
                
                # 5. 設定ファイル保存
                config = {
                    "shop_domain": shop_domain,
                    "access_token": access_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scopes": oauth.scopes
                }
                
                config_file = Path(__file__).parent.parent / "20_QA" / "shopify_oauth_config.json"
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                
                print(f"設定を保存しました: {config_file}")
                print("\n=== 次のステップ ===")
                print("1. 環境変数を設定:")
                print(f"   export SHOPIFY_SHOP_DOMAIN='{shop_domain}'")
                print(f"   export SHOPIFY_ACCESS_TOKEN='{access_token}'")
                print("2. APIテストを実行:")
                print("   python3 scripts/shopify_api_tester.py")
            else:
                print("❌ 接続テスト失敗")
        else:
            print("❌ アクセストークン取得失敗")
    else:
        print("❌ 認証コードが入力されませんでした")

if __name__ == "__main__":
    from pathlib import Path
    main()





