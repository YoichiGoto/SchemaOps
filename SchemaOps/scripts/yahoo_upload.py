#!/usr/bin/env python3
"""
Yahoo Shopping API 商品アップロードスクリプト
CSVファイルをアップロードして商品を登録・更新します
"""
import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from requests_oauthlib import OAuth1Session
import csv
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YahooShoppingAPI:
    """Yahoo Shopping API クライアント"""
    
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
    
    def upload_item_file(self, csv_file_path: str, seller_id: str) -> Dict[str, Any]:
        """
        商品CSVファイルをアップロード
        
        Args:
            csv_file_path: アップロードするCSVファイルのパス
            seller_id: セラーID（YahooショッピングのストアID）
        
        Returns:
            アップロード結果の辞書
        """
        try:
            url = f"{self.base_url}/uploadItemFile"
            
            # CSVファイルを読み込む
            if not Path(csv_file_path).exists():
                raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_file_path}")
            
            # ファイルを開いてアップロード
            with open(csv_file_path, 'rb') as f:
                files = {
                    'file': (Path(csv_file_path).name, f, 'text/csv')
                }
                params = {
                    'seller_id': seller_id
                }
                
                logger.info(f"商品CSVファイルをアップロード中: {csv_file_path}")
                response = self.oauth.post(url, files=files, params=params)
                
                if response.status_code == 200:
                    result = response.text
                    logger.info("✅ アップロード成功")
                    return {
                        'success': True,
                        'status_code': response.status_code,
                        'response': result,
                        'uploaded_at': datetime.now().isoformat()
                    }
                else:
                    logger.error(f"❌ アップロード失敗: {response.status_code} - {response.text}")
                    return {
                        'success': False,
                        'status_code': response.status_code,
                        'error': response.text,
                        'uploaded_at': datetime.now().isoformat()
                    }
        except Exception as e:
            logger.error(f"❌ アップロードエラー: {e}")
            return {
                'success': False,
                'error': str(e),
                'uploaded_at': datetime.now().isoformat()
            }
    
    def get_upload_status(self, job_id: str, seller_id: str) -> Dict[str, Any]:
        """
        アップロードジョブのステータスを取得
        
        Args:
            job_id: ジョブID
            seller_id: セラーID
        
        Returns:
            ステータス情報の辞書
        """
        try:
            url = f"{self.base_url}/getUploadStatus"
            params = {
                'seller_id': seller_id,
                'job_id': job_id
            }
            
            logger.info(f"アップロードステータスを取得中: {job_id}")
            response = self.oauth.get(url, params=params)
            
            if response.status_code == 200:
                result = response.text
                logger.info("✅ ステータス取得成功")
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'response': result
                }
            else:
                logger.error(f"❌ ステータス取得失敗: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"❌ ステータス取得エラー: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_csv_format(self, csv_file_path: str) -> Dict[str, Any]:
        """
        CSVファイルのフォーマットを検証
        
        Args:
            csv_file_path: 検証するCSVファイルのパス
        
        Returns:
            検証結果の辞書
        """
        try:
            required_columns = [
                'code',  # 商品コード（必須）
                'name',  # 商品名（必須）
                'price',  # 価格（必須）
                'url',  # 商品URL（必須）
            ]
            
            with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                columns = reader.fieldnames or []
                
                missing_columns = [col for col in required_columns if col not in columns]
                
                if missing_columns:
                    return {
                        'valid': False,
                        'error': f'必須カラムが不足しています: {", ".join(missing_columns)}',
                        'found_columns': columns,
                        'required_columns': required_columns
                    }
                
                # 行数をカウント
                row_count = sum(1 for row in reader)
                
                return {
                    'valid': True,
                    'columns': columns,
                    'row_count': row_count,
                    'message': f'CSVフォーマットは有効です（{row_count}行）'
                }
        except Exception as e:
            return {
                'valid': False,
                'error': f'CSVファイルの読み込みエラー: {str(e)}'
            }

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
    
    parser = argparse.ArgumentParser(description='Yahoo Shopping API 商品アップロード')
    parser.add_argument('csv_file', help='アップロードするCSVファイルのパス')
    parser.add_argument('--seller-id', required=True, help='セラーID（YahooショッピングのストアID）')
    parser.add_argument('--validate-only', action='store_true', help='CSVフォーマットの検証のみ実行')
    
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
    
    # APIクライアント初期化
    api = YahooShoppingAPI(client_id, client_secret, oauth_token, oauth_token_secret)
    
    # CSVファイルの検証
    print("=== CSVファイル検証 ===")
    validation_result = api.validate_csv_format(args.csv_file)
    
    if not validation_result['valid']:
        print(f"❌ CSVフォーマットエラー: {validation_result['error']}")
        if 'found_columns' in validation_result:
            print(f"   見つかったカラム: {', '.join(validation_result['found_columns'])}")
        return
    
    print(f"✅ {validation_result['message']}")
    print(f"   カラム数: {len(validation_result['columns'])}")
    print(f"   データ行数: {validation_result['row_count']}")
    print()
    
    if args.validate_only:
        print("検証のみ実行しました。")
        return
    
    # 商品アップロード
    print("=== 商品アップロード ===")
    upload_result = api.upload_item_file(args.csv_file, args.seller_id)
    
    if upload_result['success']:
        print("✅ アップロード成功")
        print(f"   レスポンス: {upload_result.get('response', 'N/A')}")
        
        # 結果を保存
        result_file = Path(__file__).parent.parent / "20_QA" / f"yahoo_upload_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(upload_result, f, ensure_ascii=False, indent=2)
        print(f"   結果を保存しました: {result_file}")
    else:
        print(f"❌ アップロード失敗")
        print(f"   エラー: {upload_result.get('error', 'N/A')}")
        if upload_result.get('status_code'):
            print(f"   ステータスコード: {upload_result['status_code']}")

if __name__ == "__main__":
    main()








