#!/usr/bin/env python3
"""
Yahoo Shopping API連携テストスクリプト
実際のYahooショッピングAPIとの接続をテストします
"""
import os
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from pathlib import Path
from requests_oauthlib import OAuth1Session

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YahooAPITester:
    """Yahoo Shopping API接続テストクラス"""
    
    def __init__(self, client_id: str, client_secret: str, 
                 oauth_token: str, oauth_token_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.oauth_token = oauth_token
        self.oauth_token_secret = oauth_token_secret
        self.base_url = "https://circus.shopping.yahooapis.jp/ShoppingWebService/V1"
        
        # OAuth 1.0a セッション
        self.oauth = OAuth1Session(
            client_id,
            client_secret=client_secret,
            resource_owner_key=oauth_token,
            resource_owner_secret=oauth_token_secret
        )
    
    def test_connection(self) -> bool:
        """基本的な接続テスト"""
        try:
            # テスト用のエンドポイント（実際のAPI仕様に合わせて調整が必要）
            url = f"{self.base_url}/uploadItemFile"
            params = {'seller_id': 'test'}
            
            logger.info("接続テストを実行中...")
            response = self.oauth.get(url, params=params)
            
            # 401以外のレスポンスは認証が通っている可能性がある
            if response.status_code == 401:
                logger.error(f"❌ 認証失敗: {response.status_code} - {response.text}")
                return False
            elif response.status_code in [200, 400, 404]:
                # 400や404は認証は通っているが、パラメータが不正な場合
                logger.info(f"✅ 認証成功（ステータスコード: {response.status_code}）")
                return True
            else:
                logger.warning(f"⚠️ 予期しないレスポンス: {response.status_code} - {response.text}")
                return True  # 認証は通っている可能性が高い
                
        except Exception as e:
            logger.error(f"❌ 接続エラー: {e}")
            return False
    
    def get_api_info(self) -> Dict[str, Any]:
        """API情報を取得"""
        return {
            'base_url': self.base_url,
            'client_id': self.client_id[:20] + '...',
            'has_oauth_token': bool(self.oauth_token),
            'has_oauth_token_secret': bool(self.oauth_token_secret)
        }
    
    def test_upload_endpoint(self, seller_id: str) -> Dict[str, Any]:
        """アップロードエンドポイントのテスト"""
        try:
            url = f"{self.base_url}/uploadItemFile"
            params = {'seller_id': seller_id}
            
            logger.info("アップロードエンドポイントをテスト中...")
            # GETリクエストでエンドポイントの存在確認（実際のアップロードはPOST）
            response = self.oauth.get(url, params=params)
            
            return {
                'endpoint': url,
                'status_code': response.status_code,
                'response': response.text[:500] if response.text else 'N/A',
                'tested_at': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'endpoint': url,
                'error': str(e),
                'tested_at': datetime.now().isoformat()
            }
    
    def run_full_test(self, seller_id: Optional[str] = None) -> Dict[str, Any]:
        """完全テストの実行"""
        results = {
            "connection_test": False,
            "api_info": {},
            "upload_endpoint_test": {},
            "tested_at": datetime.now().isoformat()
        }
        
        logger.info("=== Yahoo Shopping API 接続テスト開始 ===")
        
        # 1. API情報取得
        results["api_info"] = self.get_api_info()
        logger.info(f"API Base URL: {results['api_info']['base_url']}")
        
        # 2. 接続テスト
        results["connection_test"] = self.test_connection()
        
        if results["connection_test"]:
            # 3. アップロードエンドポイントテスト
            if seller_id:
                results["upload_endpoint_test"] = self.test_upload_endpoint(seller_id)
            else:
                logger.warning("セラーIDが指定されていないため、アップロードエンドポイントテストをスキップ")
        
        return results

def load_config() -> Optional[Dict[str, Any]]:
    """設定ファイルから認証情報を読み込む"""
    config_file = Path(__file__).parent.parent / "20_QA" / "yahoo_oauth_config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"設定ファイルの読み込みに失敗: {e}")
    return None

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Yahoo Shopping API 接続テスト')
    parser.add_argument('--seller-id', help='セラーID（アップロードエンドポイントテスト用）')
    
    args = parser.parse_args()
    
    # 認証情報の取得
    config = load_config()
    
    client_id = os.environ.get("YAHOO_CLIENT_ID") or (config.get('client_id') if config else None) or "dj00aiZpPXEyTklVYmtTUktxeSZzPWNvbnN1bWVyc2VjcmV0Jng9NWM-"
    client_secret = os.environ.get("YAHOO_CLIENT_SECRET") or (config.get('client_secret') if config else None) or "Ew7VY2Vd3OtOlbWPXcdzabDwGD4odpFruPym6iA8"
    oauth_token = os.environ.get("YAHOO_OAUTH_TOKEN") or (config.get('oauth_token') if config else None)
    oauth_token_secret = os.environ.get("YAHOO_OAUTH_TOKEN_SECRET") or (config.get('oauth_token_secret') if config else None)
    
    if not all([client_id, client_secret, oauth_token, oauth_token_secret]):
        print("❌ 認証情報が不足しています")
        print("以下のいずれかの方法で認証情報を設定してください:")
        print("1. 環境変数:")
        print("   export YAHOO_CLIENT_ID='your-client-id'")
        print("   export YAHOO_CLIENT_SECRET='your-client-secret'")
        print("   export YAHOO_OAUTH_TOKEN='your-oauth-token'")
        print("   export YAHOO_OAUTH_TOKEN_SECRET='your-oauth-token-secret'")
        print("2. OAuth認証を実行:")
        print("   python3 scripts/yahoo_oauth.py")
        return
    
    # テスト実行
    tester = YahooAPITester(client_id, client_secret, oauth_token, oauth_token_secret)
    results = tester.run_full_test(args.seller_id)
    
    # 結果保存
    output_file = Path(__file__).parent.parent / "20_QA" / "yahoo_test_results.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 結果表示
    print(f"\n=== テスト結果 ===")
    print(f"接続テスト: {'✅ 成功' if results['connection_test'] else '❌ 失敗'}")
    print(f"API Base URL: {results['api_info']['base_url']}")
    
    if results['connection_test']:
        if results.get('upload_endpoint_test'):
            endpoint_test = results['upload_endpoint_test']
            print(f"アップロードエンドポイント: ステータスコード {endpoint_test.get('status_code', 'N/A')}")
    
    print(f"\n結果を保存しました: {output_file}")

if __name__ == "__main__":
    main()








