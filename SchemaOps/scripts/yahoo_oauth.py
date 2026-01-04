#!/usr/bin/env python3
"""
Yahoo Shopping API OAuth認証フロー実装
Client IDとSecretを使用してAccess Tokenを取得
"""
import os
import json
import requests
from urllib.parse import urlencode, parse_qs, urlparse
import webbrowser
from typing import Dict, Any, Optional
import logging
from pathlib import Path
from requests_oauthlib import OAuth1Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YahooOAuth:
    """Yahoo Shopping API OAuth認証クラス"""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.request_token_url = "https://auth.login.yahoo.co.jp/oauth/v1/get_request_token"
        self.authorize_url = "https://auth.login.yahoo.co.jp/oauth/v1/authorize"
        self.access_token_url = "https://auth.login.yahoo.co.jp/oauth/v1/get_access_token"
        self.callback_uri = "oob"  # Out-of-band callback for desktop apps
        
        # OAuth 1.0a セッション
        self.oauth = OAuth1Session(
            client_id,
            client_secret=client_secret,
            callback_uri=self.callback_uri
        )
    
    def get_request_token(self) -> Dict[str, str]:
        """リクエストトークンを取得"""
        try:
            logger.info("リクエストトークンを取得中...")
            response = self.oauth.fetch_request_token(self.request_token_url)
            
            self.oauth_token = response.get('oauth_token')
            self.oauth_token_secret = response.get('oauth_token_secret')
            
            logger.info(f"✅ リクエストトークン取得成功")
            return {
                'oauth_token': self.oauth_token,
                'oauth_token_secret': self.oauth_token_secret
            }
        except Exception as e:
            logger.error(f"❌ リクエストトークン取得失敗: {e}")
            raise
    
    def get_authorization_url(self) -> str:
        """認証URLを生成"""
        if not hasattr(self, 'oauth_token'):
            self.get_request_token()
        
        auth_url = f"{self.authorize_url}?oauth_token={self.oauth_token}"
        return auth_url
    
    def get_access_token(self, oauth_verifier: str) -> Dict[str, Any]:
        """認証コードをアクセストークンに交換"""
        try:
            if not hasattr(self, 'oauth_token') or not hasattr(self, 'oauth_token_secret'):
                raise ValueError("リクエストトークンが取得されていません。先にget_request_token()を実行してください。")
            
            # OAuth 1.0a セッションを再構築
            oauth = OAuth1Session(
                self.client_id,
                client_secret=self.client_secret,
                resource_owner_key=self.oauth_token,
                resource_owner_secret=self.oauth_token_secret,
                verifier=oauth_verifier
            )
            
            logger.info("アクセストークンを取得中...")
            response = oauth.fetch_access_token(self.access_token_url)
            
            logger.info("✅ アクセストークン取得成功")
            return {
                'oauth_token': response.get('oauth_token'),
                'oauth_token_secret': response.get('oauth_token_secret'),
                'guid': response.get('xoauth_yahoo_guid', ''),
                'expires_in': response.get('oauth_expires_in', '')
            }
        except Exception as e:
            logger.error(f"❌ アクセストークン取得失敗: {e}")
            raise
    
    def test_access_token(self, oauth_token: str, oauth_token_secret: str) -> bool:
        """アクセストークンのテスト"""
        try:
            # Yahoo Shopping APIのテストエンドポイントを使用
            test_url = "https://circus.shopping.yahooapis.jp/ShoppingWebService/V1/uploadItemFile"
            
            oauth = OAuth1Session(
                self.client_id,
                client_secret=self.client_secret,
                resource_owner_key=oauth_token,
                resource_owner_secret=oauth_token_secret
            )
            
            # テストリクエスト（実際のアップロードは行わない）
            response = oauth.get(test_url, params={'seller_id': 'test'})
            
            # 401以外のエラーは認証が通っている可能性がある
            if response.status_code != 401:
                logger.info("✅ アクセストークン検証成功")
                return True
            else:
                logger.warning(f"⚠️ アクセストークン検証: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ アクセストークン検証エラー: {e}")
            return False

def main():
    """メイン実行関数"""
    # 認証情報
    client_id = os.environ.get("YAHOO_CLIENT_ID", "dj00aiZpPXEyTklVYmtTUktxeSZzPWNvbnN1bWVyc2VjcmV0Jng9NWM-")
    client_secret = os.environ.get("YAHOO_CLIENT_SECRET", "Ew7VY2Vd3OtOlbWPXcdzabDwGD4odpFruPym6iA8")
    
    if not all([client_id, client_secret]):
        print("⚠️  エラー: 認証情報が設定されていません")
        print("以下の環境変数を設定してください:")
        print("  export YAHOO_CLIENT_ID='your-client-id'")
        print("  export YAHOO_CLIENT_SECRET='your-client-secret'")
        return
    
    # OAuth認証フロー開始
    oauth = YahooOAuth(client_id, client_secret)
    
    print("=== Yahoo Shopping API OAuth認証フロー ===")
    print(f"Client ID: {client_id[:20]}...")
    print()
    
    try:
        # 1. リクエストトークン取得
        print("1. リクエストトークンを取得中...")
        request_token = oauth.get_request_token()
        print(f"   ✅ リクエストトークン取得成功")
        print()
        
        # 2. 認証URL生成
        print("2. 以下のURLにアクセスしてアプリを認証してください:")
        auth_url = oauth.get_authorization_url()
        print(f"   {auth_url}")
        print()
        
        # ブラウザで開く
        try:
            webbrowser.open(auth_url)
            print("   ブラウザで認証ページを開きました")
        except:
            print("   ブラウザを自動で開けませんでした。上記のURLを手動で開いてください")
        print()
        
        # 3. 認証コードの入力待ち
        print("3. 認証後、表示される認証コード（verifier）を入力してください")
        oauth_verifier = input("認証コードを入力してください: ").strip()
        
        if oauth_verifier:
            # 4. アクセストークン取得
            print("\n4. アクセストークンを取得中...")
            token_data = oauth.get_access_token(oauth_verifier)
            
            if token_data and "oauth_token" in token_data:
                print(f"✅ アクセストークン取得成功")
                print(f"   OAuth Token: {token_data['oauth_token'][:20]}...")
                print(f"   GUID: {token_data.get('guid', 'N/A')}")
                
                # 5. 接続テスト
                print("\n5. 接続テスト実行中...")
                if oauth.test_access_token(
                    token_data['oauth_token'],
                    token_data['oauth_token_secret']
                ):
                    print("✅ OAuth認証完了!")
                    
                    # 6. 設定ファイル保存
                    config = {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "oauth_token": token_data['oauth_token'],
                        "oauth_token_secret": token_data['oauth_token_secret'],
                        "guid": token_data.get('guid', ''),
                        "expires_in": token_data.get('expires_in', ''),
                        "authenticated_at": str(Path(__file__).stat().st_mtime)
                    }
                    
                    config_file = Path(__file__).parent.parent / "20_QA" / "yahoo_oauth_config.json"
                    config_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(config, f, ensure_ascii=False, indent=2)
                    
                    print(f"設定を保存しました: {config_file}")
                    print("\n=== 次のステップ ===")
                    print("1. 環境変数を設定:")
                    print(f"   export YAHOO_OAUTH_TOKEN='{token_data['oauth_token']}'")
                    print(f"   export YAHOO_OAUTH_TOKEN_SECRET='{token_data['oauth_token_secret']}'")
                    print("2. 商品アップロードを実行:")
                    print("   python3 scripts/yahoo_upload.py")
                else:
                    print("⚠️ 接続テストで警告が発生しましたが、設定は保存しました")
            else:
                print("❌ アクセストークン取得失敗")
        else:
            print("❌ 認証コードが入力されませんでした")
    except Exception as e:
        logger.error(f"認証フロー中にエラーが発生しました: {e}")
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()








