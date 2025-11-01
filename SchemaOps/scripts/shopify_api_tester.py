#!/usr/bin/env python3
"""
Shopify API連携テストスクリプト
実際のShopifyストアとの接続をテストします
"""
import os
import json
import requests
from datetime import datetime
from typing import Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ShopifyAPITester:
    """Shopify API接続テストクラス"""
    
    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.base_url = f"https://{shop_domain}/admin/api/2024-01"
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token
        }
    
    def test_connection(self) -> bool:
        """基本的な接続テスト"""
        try:
            # ショップ情報取得でテスト
            url = f"{self.base_url}/shop.json"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                shop_data = response.json()
                logger.info(f"✅ 接続成功: {shop_data['shop']['name']}")
                return True
            else:
                logger.error(f"❌ 接続失敗: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 接続エラー: {e}")
            return False
    
    def get_product_schema(self) -> Dict[str, Any]:
        """商品スキーマの取得"""
        try:
            # 商品一覧取得
            url = f"{self.base_url}/products.json?limit=5"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                products_data = response.json()
                schema = self._analyze_product_schema(products_data)
                logger.info(f"✅ 商品スキーマ取得成功: {len(schema['attributes'])}属性")
                return schema
            else:
                logger.error(f"❌ 商品スキーマ取得失敗: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ 商品スキーマ取得エラー: {e}")
            return {}
    
    def _analyze_product_schema(self, products_data: Dict[str, Any]) -> Dict[str, Any]:
        """商品データからスキーマを分析"""
        attributes = []
        
        if products_data.get('products'):
            # 最初の商品からスキーマを抽出
            sample_product = products_data['products'][0]
            
            # 基本属性
            basic_attrs = [
                'id', 'title', 'body_html', 'vendor', 'product_type', 
                'tags', 'handle', 'created_at', 'updated_at'
            ]
            
            for attr in basic_attrs:
                if attr in sample_product:
                    value = sample_product[attr]
                    attributes.append({
                        "name": attr,
                        "required": attr in ['id', 'title'],
                        "dataType": self._infer_data_type(value),
                        "maxLength": self._get_max_length(value),
                        "description": self._get_description(attr)
                    })
            
            # variants属性
            if 'variants' in sample_product and sample_product['variants']:
                attributes.append({
                    "name": "variants",
                    "required": True,
                    "dataType": "array",
                    "description": "Product variants"
                })
            
            # images属性
            if 'images' in sample_product and sample_product['images']:
                attributes.append({
                    "name": "images",
                    "required": False,
                    "dataType": "array",
                    "description": "Product images"
                })
        
        return {
            "attributes": attributes,
            "extractedAt": datetime.now().isoformat(),
            "source": "shopify_admin_api",
            "version": "2024-01",
            "shop_domain": self.shop_domain
        }
    
    def _infer_data_type(self, value) -> str:
        """値からデータ型を推論"""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "decimal"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "string"
    
    def _get_max_length(self, value) -> int:
        """文字列の最大長を取得"""
        if isinstance(value, str):
            return len(value)
        return None
    
    def _get_description(self, attr_name: str) -> str:
        """属性の説明を取得"""
        descriptions = {
            "id": "Product ID",
            "title": "Product title",
            "body_html": "Product description HTML",
            "vendor": "Product vendor",
            "product_type": "Product type",
            "tags": "Product tags (comma-separated)",
            "handle": "Product URL handle",
            "created_at": "Creation timestamp",
            "updated_at": "Last update timestamp"
        }
        return descriptions.get(attr_name, f"Product {attr_name}")
    
    def test_metafields(self) -> Dict[str, Any]:
        """メタフィールドのテスト"""
        try:
            # メタフィールド定義取得
            url = f"{self.base_url}/metafields.json?limit=10"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                metafields_data = response.json()
                logger.info(f"✅ メタフィールド取得成功: {len(metafields_data.get('metafields', []))}件")
                return metafields_data
            else:
                logger.error(f"❌ メタフィールド取得失敗: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ メタフィールド取得エラー: {e}")
            return {}
    
    def run_full_test(self) -> Dict[str, Any]:
        """完全テストの実行"""
        results = {
            "connection_test": False,
            "product_schema": {},
            "metafields": {},
            "tested_at": datetime.now().isoformat()
        }
        
        logger.info("=== Shopify API 接続テスト開始 ===")
        
        # 1. 接続テスト
        results["connection_test"] = self.test_connection()
        
        if results["connection_test"]:
            # 2. 商品スキーマ取得
            results["product_schema"] = self.get_product_schema()
            
            # 3. メタフィールドテスト
            results["metafields"] = self.test_metafields()
        
        return results

def main():
    """メイン実行関数"""
    # 環境変数から認証情報を取得
    shop_domain = os.getenv('SHOPIFY_SHOP_DOMAIN')
    access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
    
    if not shop_domain or not access_token:
        print("❌ 環境変数が設定されていません")
        print("以下の環境変数を設定してください:")
        print("export SHOPIFY_SHOP_DOMAIN='your-shop.myshopify.com'")
        print("export SHOPIFY_ACCESS_TOKEN='shpat_xxxxxxxxxxxxxxxxxxxxx'")
        return
    
    # テスト実行
    tester = ShopifyAPITester(shop_domain, access_token)
    results = tester.run_full_test()
    
    # 結果保存
    output_file = Path(__file__).parent.parent / "20_QA" / "shopify_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 結果表示
    print(f"\n=== テスト結果 ===")
    print(f"接続テスト: {'✅ 成功' if results['connection_test'] else '❌ 失敗'}")
    
    if results['connection_test']:
        schema = results['product_schema']
        print(f"商品スキーマ: {len(schema.get('attributes', []))}属性")
        print(f"メタフィールド: {len(results['metafields'].get('metafields', []))}件")
        
        print(f"\n=== 抽出された属性 ===")
        for attr in schema.get('attributes', []):
            print(f"- {attr['name']}: {attr['dataType']} ({'必須' if attr['required'] else '任意'})")
    
    print(f"\n結果を保存しました: {output_file}")

if __name__ == "__main__":
    from pathlib import Path
    main()





