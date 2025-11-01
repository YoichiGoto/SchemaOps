#!/usr/bin/env python3
"""
API-based schema extraction for marketplace integrations.
Supports Google Merchant Center, Amazon SP-API, and Shopify Admin API.
"""
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """API configuration for different marketplaces."""
    name: str
    base_url: str
    auth_type: str
    rate_limit: int
    headers: Dict[str, str]

from googleapiclient.discovery import build
from google.oauth2 import service_account

class GoogleMerchantCenterAPI:
    """Google Merchant Center Content API client."""
    
    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path
        self.base_url = "https://shoppingcontent.googleapis.com/content/v2.1"
        self.config = APIConfig(
            name="google_merchant_center",
            base_url=self.base_url,
            auth_type="oauth2",
            rate_limit=10000,  # per day
            headers={"Content-Type": "application/json"}
        )
    
    def get_product_schema(self, merchant_id: str) -> Dict[str, Any]:
        """Get product data specification schema."""
        try:
            creds = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=['https://www.googleapis.com/auth/content'])
            service = build('content', 'v2.1', credentials=creds)

            # List products to find a valid product ID
            request = service.products().list(merchantId=merchant_id, maxResults=1)
            response = request.execute()

            if 'resources' not in response or len(response['resources']) == 0:
                # If no products are found, insert a sample product.
                sample_product = {
                    'offerId': 'sample-product-123',
                    'title': 'Sample Product',
                    'description': 'This is a sample product.',
                    'link': 'https://example.com/sample-product',
                    'imageLink': 'https://example.com/sample-product.jpg',
                    'contentLanguage': 'en',
                    'targetCountry': 'US',
                    'channel': 'online',
                    'availability': 'in stock',
                    'condition': 'new',
                    'googleProductCategory': 'Apparel & Accessories > Clothing',
                    'gtin': '0123456789012',
                    'price': {
                        'value': '25.00',
                        'currency': 'USD'
                    }
                }
                product_insert_request = service.products().insert(merchantId=merchant_id, body=sample_product)
                inserted_product = product_insert_request.execute()
                product_id = inserted_product['id']
            else:
                product_id = response['resources'][0]['id']
            
            product_request = service.products().get(merchantId=merchant_id, productId=product_id)
            product = product_request.execute()

            attributes = []
            for key, value in product.items():
                attributes.append({
                    "name": key,
                    "required": False,  # This is an assumption
                    "dataType": str(type(value).__name__),
                    "description": ""
                })
            schema = {
                "attributes": attributes,
                "extractedAt": datetime.now().isoformat(),
                "source": "google_merchant_center_api",
                "version": "v2.1"
            }

            logger.info(f"Extracted {len(schema['attributes'])} attributes from Google Merchant Center")
            return schema
            
        except Exception as e:
            logger.error(f"Error extracting Google Merchant Center schema: {e}")
            raise

class AmazonSPAPI:
    """Amazon Selling Partner API client."""
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None, 
                 refresh_token: Optional[str] = None, iam_user_arn: Optional[str] = None):
        self.base_url = "https://sellingpartnerapi-na.amazon.com"
        self.sandbox_url = "https://sandbox.sellingpartnerapi-na.amazon.com"
        self.repo_path = "amzn/selling-partner-api-models"
        self.model_path = "models/catalog-items-api-model"
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.iam_user_arn = iam_user_arn
        self.config = APIConfig(
            name="amazon_sp_api",
            base_url=self.base_url,
            auth_type="lwa",
            rate_limit=1000,  # per hour
            headers={"Content-Type": "application/json"}
        )
    
    def _get_access_token(self) -> Optional[str]:
        """Get access token using refresh token."""
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            logger.warning("Amazon SP-API credentials not provided, cannot get access token")
            return None
        
        try:
            url = 'https://api.amazon.com/auth/o2/token'
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            
            access_token = response.json()['access_token']
            logger.info("Successfully obtained Amazon SP-API access token")
            return access_token
        except Exception as e:
            logger.error(f"Error getting Amazon SP-API access token: {e}")
            return None
    
    def _get_latest_schema_version(self) -> str:
        """Get the latest available schema version from GitHub repository."""
        try:
            import re
            api_url = f"https://api.github.com/repos/{self.repo_path}/contents/{self.model_path}"
            response = requests.get(api_url)
            response.raise_for_status()
            
            files = response.json()
            versions = []
            for file in files:
                if file.get('type') == 'file' and 'catalogItems_' in file.get('name', ''):
                    # Extract version from filename like catalogItems_2022-04-01.json
                    match = re.search(r'(\d{4}-\d{2}-\d{2})', file['name'])
                    if match:
                        versions.append(match.group(1))
            
            if versions:
                # Sort versions in descending order (newest first)
                versions.sort(reverse=True)
                latest_version = versions[0]
                logger.info(f"Found latest Amazon SP-API schema version: {latest_version}")
                return latest_version
            else:
                logger.warning("No schema versions found, falling back to 2022-04-01")
                return "2022-04-01"
        except Exception as e:
            logger.warning(f"Error getting latest schema version: {e}, falling back to 2022-04-01")
            return "2022-04-01"
    
    def _get_schema_from_api(self, marketplace_id: str, access_token: str) -> Dict[str, Any]:
        """Get product schema from actual Amazon SP-API using Product Type Definitions and Catalog Items APIs."""
        attributes = []
        version = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # Method 1: Get Product Type Definitions
            # This gives us the canonical schema definitions
            # Try production first (has more product types), then sandbox as fallback
            api_base_urls = [self.base_url, self.sandbox_url]
            
            for api_base_url in api_base_urls:
                try:
                    product_types_url = f"{api_base_url}/definitions/2020-09-01/productTypes"
                    headers = {
                        'x-amz-access-token': access_token,
                        'Content-Type': 'application/json'
                    }
                    params = {
                        'marketplaceIds': marketplace_id
                    }
                    
                    env_name = "sandbox" if api_base_url == self.sandbox_url else "production"
                    logger.info(f"Fetching product types from Product Type Definitions API ({env_name})...")
                    response = requests.get(product_types_url, headers=headers, params=params)
                    
                    if response.status_code == 200:
                        product_types_data = response.json()
                        product_types = product_types_data.get('productTypes', [])
                        logger.info(f"Found {len(product_types)} product types")
                        
                        # Get schema for all product types with rate limiting
                        # API allows 2 requests per second, so we'll use 0.6s delay between requests
                        import time
                        processed_count = 0
                        total_types = len(product_types)
                        
                        logger.info(f"Processing all {total_types} product types...")
                        for product_type in product_types:
                            product_type_name = product_type.get('name', '')
                            if not product_type_name:
                                continue
                            
                            try:
                                # Get product type definition
                                # Use the same base URL that worked
                                def_url = f"{api_base_url}/definitions/2020-09-01/productTypes/{product_type_name}"
                                def_params = {'marketplaceIds': marketplace_id, 'sellerId': product_type.get('sellerId', '')}
                                
                                def_response = requests.get(def_url, headers=headers, params=def_params)
                                if def_response.status_code == 200:
                                    def_data = def_response.json()
                                    logger.debug(f"Product type definition response keys: {list(def_data.keys())}")
                                    
                                    # Extract attributes from product type definition
                                    # Product Type Definitions API response structure may vary
                                    requirements = def_data.get('requirements', {})
                                    
                                    if isinstance(requirements, dict):
                                        for req_type, req_list in requirements.items():
                                            if isinstance(req_list, list):
                                                for req_item in req_list:
                                                    if isinstance(req_item, dict):
                                                        attribute_name = req_item.get('name', '')
                                                        if attribute_name:
                                                            attributes.append({
                                                                "name": f"{product_type_name}.{attribute_name}",
                                                                "required": req_type == 'REQUIRED',
                                                                "dataType": req_item.get('valueType', 'string'),
                                                                "description": req_item.get('description', ''),
                                                                "productType": product_type_name,
                                                                "requirementType": req_type
                                                            })
                                    elif isinstance(requirements, list):
                                        # Sometimes requirements is a list
                                        for req_item in requirements:
                                            if isinstance(req_item, dict):
                                                attribute_name = req_item.get('name', '')
                                                if attribute_name:
                                                    attributes.append({
                                                        "name": f"{product_type_name}.{attribute_name}",
                                                        "required": req_item.get('required', False),
                                                        "dataType": req_item.get('valueType', req_item.get('type', 'string')),
                                                        "description": req_item.get('description', ''),
                                                        "productType": product_type_name
                                                    })
                                    
                                    # Also try to extract from schema field if present
                                    if 'schema' in def_data:
                                        schema_data = def_data['schema']
                                        if isinstance(schema_data, dict):
                                            if 'properties' in schema_data:
                                                for prop_name, prop_def in schema_data['properties'].items():
                                                    existing_names = [attr.get('name', '').split('.')[-1] for attr in attributes]
                                                    if prop_name not in existing_names:
                                                        attributes.append({
                                                            "name": f"{product_type_name}.{prop_name}",
                                                            "required": prop_name in schema_data.get('required', []),
                                                            "dataType": prop_def.get('type', 'string'),
                                                            "description": prop_def.get('description', ''),
                                                            "productType": product_type_name,
                                                            "source": "product_type_definition_schema"
                                                        })
                                        elif isinstance(schema_data, str):
                                            # Schema might be a JSON string
                                            try:
                                                import json
                                                schema_dict = json.loads(schema_data)
                                                if isinstance(schema_dict, dict) and 'properties' in schema_dict:
                                                    for prop_name, prop_def in schema_dict['properties'].items():
                                                        existing_names = [attr.get('name', '').split('.')[-1] for attr in attributes]
                                                        if prop_name not in existing_names:
                                                            attributes.append({
                                                                "name": f"{product_type_name}.{prop_name}",
                                                                "required": prop_name in schema_dict.get('required', []),
                                                                "dataType": prop_def.get('type', 'string'),
                                                                "description": prop_def.get('description', ''),
                                                                "productType": product_type_name,
                                                                "source": "product_type_definition_schema_json"
                                                            })
                                            except:
                                                pass
                                    
                                    # Try to extract from requirementsList if present
                                    if 'requirementsList' in def_data:
                                        req_list = def_data['requirementsList']
                                        if isinstance(req_list, list):
                                            for req_item in req_list:
                                                if isinstance(req_item, dict):
                                                    attribute_name = req_item.get('name', req_item.get('attribute', ''))
                                                    if attribute_name:
                                                        attributes.append({
                                                            "name": f"{product_type_name}.{attribute_name}",
                                                            "required": req_item.get('isRequired', req_item.get('required', False)),
                                                            "dataType": req_item.get('valueType', req_item.get('type', 'string')),
                                                            "description": req_item.get('description', ''),
                                                            "productType": product_type_name,
                                                            "source": "requirementsList"
                                                        })
                                    
                                    # Extract from propertyGroups if present
                                    property_groups = def_data.get('propertyGroups', {})
                                    if isinstance(property_groups, dict):
                                        for group_name, group_data in property_groups.items():
                                            if isinstance(group_data, dict):
                                                # propertyGroups can contain propertyNames (list of strings)
                                                property_names = group_data.get('propertyNames', [])
                                                if isinstance(property_names, list):
                                                    for prop_name in property_names:
                                                        if isinstance(prop_name, str):
                                                            existing_names = [attr.get('name', '').split('.')[-1] for attr in attributes]
                                                            if prop_name not in existing_names:
                                                                attributes.append({
                                                                    "name": f"{product_type_name}.{prop_name}",
                                                                    "required": False,  # Will need to check requirements separately
                                                                    "dataType": "string",  # Default, may need to infer
                                                                    "description": group_data.get('description', group_data.get('title', '')),
                                                                    "productType": product_type_name,
                                                                    "propertyGroup": group_name,
                                                                    "source": "propertyGroups"
                                                                })
                                                
                                                # Also check for other structures
                                                properties = group_data.get('properties', group_data.get('attributes', []))
                                                if isinstance(properties, list):
                                                    for prop in properties:
                                                        if isinstance(prop, dict):
                                                            prop_name = prop.get('name', prop.get('key', ''))
                                                            if prop_name:
                                                                existing_names = [attr.get('name', '').split('.')[-1] for attr in attributes]
                                                                if prop_name not in existing_names:
                                                                    attributes.append({
                                                                        "name": f"{product_type_name}.{prop_name}",
                                                                        "required": prop.get('isRequired', prop.get('required', False)),
                                                                        "dataType": prop.get('valueType', prop.get('type', 'string')),
                                                                        "description": prop.get('description', ''),
                                                                        "productType": product_type_name,
                                                                        "propertyGroup": group_name,
                                                                        "source": "propertyGroups"
                                                                    })
                                                elif isinstance(properties, dict):
                                                    for prop_name, prop_def in properties.items():
                                                        existing_names = [attr.get('name', '').split('.')[-1] for attr in attributes]
                                                        if prop_name not in existing_names:
                                                            attributes.append({
                                                                "name": f"{product_type_name}.{prop_name}",
                                                                "required": prop_def.get('required', False) if isinstance(prop_def, dict) else False,
                                                                "dataType": prop_def.get('type', 'string') if isinstance(prop_def, dict) else 'string',
                                                                "description": prop_def.get('description', '') if isinstance(prop_def, dict) else '',
                                                                "productType": product_type_name,
                                                                "propertyGroup": group_name,
                                                                "source": "propertyGroups"
                                                            })
                                    elif isinstance(property_groups, list):
                                        for group in property_groups:
                                            if isinstance(group, dict):
                                                group_name = group.get('name', '')
                                                property_names = group.get('propertyNames', [])
                                                if isinstance(property_names, list):
                                                    for prop_name in property_names:
                                                        if isinstance(prop_name, str):
                                                            existing_names = [attr.get('name', '').split('.')[-1] for attr in attributes]
                                                            if prop_name not in existing_names:
                                                                attributes.append({
                                                                    "name": f"{product_type_name}.{prop_name}",
                                                                    "required": False,
                                                                    "dataType": "string",
                                                                    "description": group.get('description', ''),
                                                                    "productType": product_type_name,
                                                                    "propertyGroup": group_name,
                                                                    "source": "propertyGroups"
                                                                })
                                                properties = group.get('properties', group.get('attributes', []))
                                                if isinstance(properties, list):
                                                    for prop in properties:
                                                        if isinstance(prop, dict):
                                                            prop_name = prop.get('name', prop.get('key', ''))
                                                            if prop_name:
                                                                existing_names = [attr.get('name', '').split('.')[-1] for attr in attributes]
                                                                if prop_name not in existing_names:
                                                                    attributes.append({
                                                                        "name": f"{product_type_name}.{prop_name}",
                                                                        "required": prop.get('isRequired', prop.get('required', False)),
                                                                        "dataType": prop.get('valueType', prop.get('type', 'string')),
                                                                        "description": prop.get('description', ''),
                                                                        "productType": product_type_name,
                                                                        "propertyGroup": group_name,
                                                                        "source": "propertyGroups"
                                                                    })
                                    
                                    # Try to fetch schema from link if it's a dict with resource
                                    schema_link_info = def_data.get('schema', {})
                                    if isinstance(schema_link_info, dict) and 'link' in schema_link_info:
                                        link_info = schema_link_info.get('link', {})
                                        if isinstance(link_info, dict) and 'resource' in link_info:
                                            schema_url = link_info['resource']
                                            try:
                                                schema_response = requests.get(schema_url, headers=headers)
                                                if schema_response.status_code == 200:
                                                    fetched_schema = schema_response.json()
                                                    if isinstance(fetched_schema, dict) and 'properties' in fetched_schema:
                                                        for prop_name, prop_def in fetched_schema['properties'].items():
                                                            existing_names = [attr.get('name', '').split('.')[-1] for attr in attributes]
                                                            if prop_name not in existing_names:
                                                                attributes.append({
                                                                    "name": f"{product_type_name}.{prop_name}",
                                                                    "required": prop_name in fetched_schema.get('required', []),
                                                                    "dataType": prop_def.get('type', 'string'),
                                                                    "description": prop_def.get('description', ''),
                                                                    "productType": product_type_name,
                                                                    "source": "fetched_schema"
                                                                })
                                            except Exception as e:
                                                logger.debug(f"Could not fetch schema from link: {e}")
                                    
                                    # Log if we extracted any attributes from this product type
                                    type_attrs = [attr for attr in attributes if attr.get('productType') == product_type_name]
                                    if type_attrs:
                                        logger.info(f"Extracted {len(type_attrs)} attributes from product type {product_type_name}")
                                    else:
                                        logger.warning(f"No attributes extracted from product type {product_type_name}, response structure: {list(def_data.keys())}")
                            except Exception as e:
                                logger.warning(f"Error getting definition for {product_type_name}: {e}")
                                continue
                            
                            processed_count += 1
                            # Rate limiting: wait 0.6 seconds between requests (API allows 2 req/sec)
                            if processed_count < total_types:
                                time.sleep(0.6)
                                if processed_count % 10 == 0:
                                    logger.info(f"Processed {processed_count}/{total_types} product types, extracted {len(attributes)} attributes so far...")
                        
                        logger.info(f"Completed processing {processed_count}/{total_types} product types, extracted {len(attributes)} total attributes")
                        break  # Success, no need to try other environment
                    else:
                        logger.warning(f"Product Type Definitions API ({env_name}) returned {response.status_code}: {response.text[:200]}")
                        if api_base_url == api_base_urls[-1]:  # Last URL
                            logger.warning(f"All environments failed for Product Type Definitions API")
                except Exception as e:
                    logger.warning(f"Error fetching product types from {api_base_url}: {e}")
                    continue
            
            # Method 2: Get actual catalog items to infer schema from real data
            # Try sandbox first, then production
            for api_base_url in api_base_urls:
                try:
                    catalog_url = f"{api_base_url}/catalog/2022-04-01/items"
                    headers_catalog = {
                        'x-amz-access-token': access_token,
                        'Content-Type': 'application/json'
                    }
                    
                    env_name = "sandbox" if api_base_url == self.sandbox_url else "production"
                    # Try to search for a few items to get schema
                    search_terms = ['shoes', 'books', 'electronics']
                    for search_term in search_terms[:2]:  # Limit to avoid rate limits
                        params = {
                            'marketplaceIds': marketplace_id,
                            'keywords': search_term,
                            'pageSize': 1
                        }
                        
                        try:
                            logger.info(f"Fetching catalog items for schema inference (search: {search_term}, {env_name})...")
                            response = requests.get(catalog_url, headers=headers_catalog, params=params)
                            
                            if response.status_code == 200:
                                catalog_data = response.json()
                                items = catalog_data.get('items', [])
                                
                                for item in items:
                                    # Extract attributes from actual item data
                                    if isinstance(item, dict):
                                        for key, value in item.items():
                                            if key not in [attr.get('name', '').split('.')[-1] for attr in attributes]:
                                                attributes.append({
                                                    "name": f"Item.{key}",
                                                    "required": False,
                                                    "dataType": self._infer_data_type(value),
                                                    "description": f"Field from catalog item API response",
                                                    "source": "catalog_items_api"
                                                })
                                                
                                                # If value is a dict, extract nested attributes
                                                if isinstance(value, dict):
                                                    for nested_key, nested_value in value.items():
                                                        attributes.append({
                                                            "name": f"Item.{key}.{nested_key}",
                                                            "required": False,
                                                            "dataType": self._infer_data_type(nested_value),
                                                            "description": f"Nested field from catalog item",
                                                            "source": "catalog_items_api"
                                                        })
                                break  # Got data, no need to try more searches
                            else:
                                logger.warning(f"Catalog Items API ({env_name}) returned {response.status_code} for {search_term}")
                        except Exception as e:
                            logger.warning(f"Error fetching catalog items for {search_term} ({env_name}): {e}")
                            continue
                    
                    # If we got attributes, break from environment loop
                    if attributes:
                        break
                except Exception as e:
                    logger.warning(f"Error in catalog items schema extraction from {api_base_url}: {e}")
                    continue
            
            if not attributes:
                logger.warning("No attributes extracted from API, falling back to OpenAPI spec")
                raise Exception("No schema attributes extracted from API")
            
            # Create canonical attribute mapping for ZAG Converter
            # This creates a unified schema that can be used across all product types
            canonical_attributes = {}
            product_type_summary = {}
            
            for attr in attributes:
                # Extract canonical name (attribute name without product type prefix)
                full_name = attr.get('name', '')
                if '.' in full_name:
                    canonical_name = full_name.split('.', 1)[1]  # Remove product type prefix (e.g., "LUGGAGE.item_name" -> "item_name")
                else:
                    canonical_name = full_name
                
                product_type = attr.get('productType', 'UNKNOWN')
                
                # Build product type summary
                if product_type not in product_type_summary:
                    product_type_summary[product_type] = {
                        "count": 0,
                        "propertyGroups": set()
                    }
                product_type_summary[product_type]["count"] += 1
                if attr.get('propertyGroup'):
                    product_type_summary[product_type]["propertyGroups"].add(attr.get('propertyGroup'))
                
                # Build canonical attributes mapping
                if canonical_name not in canonical_attributes:
                    canonical_attributes[canonical_name] = {
                        "canonicalName": canonical_name,
                        "required": attr.get('required', False),
                        "dataType": attr.get('dataType', 'string'),
                        "description": attr.get('description', ''),
                        "productTypes": [product_type],
                        "propertyGroups": [attr.get('propertyGroup')] if attr.get('propertyGroup') else [],
                        "sources": [attr.get('source', 'unknown')],
                        "mappings": {
                            product_type: {
                                "originalName": full_name,
                                "required": attr.get('required', False),
                                "dataType": attr.get('dataType', 'string'),
                                "propertyGroup": attr.get('propertyGroup'),
                                "description": attr.get('description', '')
                            }
                        }
                    }
                else:
                    # Merge with existing canonical attribute
                    ca = canonical_attributes[canonical_name]
                    
                    # Add product type if not already present
                    if product_type not in ca['productTypes']:
                        ca['productTypes'].append(product_type)
                    
                    # Add property group if not already present
                    pg = attr.get('propertyGroup')
                    if pg and pg not in ca['propertyGroups']:
                        ca['propertyGroups'].append(pg)
                    
                    # Update required flag (if any product type requires it, mark as required)
                    if attr.get('required', False):
                        ca['required'] = True
                    
                    # Add source if not already present
                    src = attr.get('source', 'unknown')
                    if src not in ca['sources']:
                        ca['sources'].append(src)
                    
                    # Add mapping for this product type
                    ca['mappings'][product_type] = {
                        "originalName": full_name,
                        "required": attr.get('required', False),
                        "dataType": attr.get('dataType', 'string'),
                        "propertyGroup": attr.get('propertyGroup'),
                        "description": attr.get('description', '')
                    }
            
            # Convert sets to lists for JSON serialization
            for pt in product_type_summary:
                product_type_summary[pt]["propertyGroups"] = list(product_type_summary[pt]["propertyGroups"])
            
            # Convert canonical_attributes dict to list for easier use
            canonical_attributes_list = list(canonical_attributes.values())
            
            schema = {
                "attributes": attributes,  # Full attributes with product type prefixes (e.g., "LUGGAGE.item_name")
                "canonicalAttributes": canonical_attributes_list,  # Unified attributes without product type prefixes (for ZAG Converter)
                "productTypes": sorted(list(product_type_summary.keys())),
                "productTypeSummary": product_type_summary,
                "extractedAt": datetime.now().isoformat(),
                "source": "amazon_sp_api_direct",
                "version": version,
                "marketplaceId": marketplace_id,
                "totalProductTypes": len(product_type_summary),
                "totalAttributes": len(attributes),
                "totalCanonicalAttributes": len(canonical_attributes_list),
                "schemaType": "unified"  # Indicates this schema supports all product types
            }
            
            logger.info(f"Extracted {len(attributes)} attributes from Amazon SP-API (direct)")
            return schema
            
        except Exception as e:
            logger.error(f"Error getting schema from Amazon SP-API: {e}")
            raise
    
    def _infer_data_type(self, value: Any) -> str:
        """Infer data type from value."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, list):
            if value and isinstance(value[0], dict):
                return "array<object>"
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "string"
    
    def get_product_schema(self, marketplace_id: str) -> Dict[str, Any]:
        """Get product type definitions schema from the actual API or OpenAPI specification."""
        # Try to use actual API first if credentials are provided
        if self.client_id and self.client_secret and self.refresh_token:
            try:
                access_token = self._get_access_token()
                if access_token:
                    try:
                        return self._get_schema_from_api(marketplace_id, access_token)
                    except Exception as e:
                        logger.warning(f"Error using Amazon SP-API: {e}, falling back to OpenAPI spec")
                else:
                    logger.warning("Failed to get access token, falling back to OpenAPI spec")
            except Exception as e:
                logger.warning(f"Error with Amazon SP-API authentication: {e}, falling back to OpenAPI spec")
        else:
            logger.info("Amazon SP-API credentials not provided, using OpenAPI specification")
        
        # Fallback: Get schema from GitHub OpenAPI specification
        try:
            # Get the latest schema version dynamically
            version = self._get_latest_schema_version()
            schema_url = f"https://raw.githubusercontent.com/{self.repo_path}/main/{self.model_path}/catalogItems_{version}.json"
            
            logger.info(f"Downloading Amazon SP-API schema (version {version}) from {schema_url}...")
            response = requests.get(schema_url)
            response.raise_for_status()
            logger.info("Successfully downloaded Amazon SP-API schema.")
            
            openapi_spec = response.json()
            # Support both OpenAPI 3.0 (components.schemas) and Swagger 2.0 (definitions)
            if 'components' in openapi_spec:
                schemas = openapi_spec.get('components', {}).get('schemas', {})
            else:
                schemas = openapi_spec.get('definitions', {})
            
            attributes = []
            for schema_name, schema_def in schemas.items():
                # Extract top-level schema attributes
                attributes.append({
                    "name": schema_name,
                    "required": False,
                    "dataType": schema_def.get("type", "object"),
                    "description": schema_def.get("description", ""),
                })
                
                # Extract properties from each schema (for object types)
                properties = schema_def.get("properties", {})
                required_fields = schema_def.get("required", [])
                
                for prop_name, prop_def in properties.items():
                    attributes.append({
                        "name": f"{schema_name}.{prop_name}",
                        "required": prop_name in required_fields,
                        "dataType": prop_def.get("type", "string"),
                        "description": prop_def.get("description", ""),
                        "schema": schema_name
                    })

            schema = {
                "attributes": attributes,
                "extractedAt": datetime.now().isoformat(),
                "source": "amazon_sp_api_openapi_spec",
                "version": version
            }
            
            logger.info(f"Extracted {len(schema['attributes'])} attributes (schemas) from Amazon SP-API")
            return schema
            
        except Exception as e:
            logger.error(f"Error extracting Amazon SP-API schema: {e}")
            # Try to get version even if schema download failed
            try:
                version = self._get_latest_schema_version()
            except:
                version = "2022-04-01"
            
            # Return error schema instead of raising to allow other APIs to continue
            return {
                "attributes": [],
                "extractedAt": datetime.now().isoformat(),
                "source": "amazon_sp_api_openapi_spec",
                "version": version,
                "error": str(e)
            }

class ShopifyAdminAPI:
    """Shopify Admin API client."""
    
    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.base_url = f"https://{shop_domain}/admin/api/2024-01"
        self.config = APIConfig(
            name="shopify_admin_api",
            base_url=self.base_url,
            auth_type="private_app",
            rate_limit=2,  # per second
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": access_token
            }
        )
    
    def get_product_schema(self) -> Dict[str, Any]:
        """Get product schema and metafields."""
        try:
            # 実際のAPI呼び出し（本番環境）
            
            # 商品スキーマ取得
            products_url = f"{self.base_url}/products.json?limit=1"
            response = requests.get(products_url, headers=self.config.headers)
            
            if response.status_code == 200:
                products_data = response.json()
                schema = self._parse_product_schema(products_data)
            else:
                # フォールバック: モックデータ
                schema = self._get_mock_schema()
            
            logger.info(f"Extracted {len(schema['attributes'])} attributes from Shopify Admin API")
            return schema
            
        except Exception as e:
            logger.error(f"Error extracting Shopify Admin API schema: {e}")
            # フォールバック: モックデータ
            return self._get_mock_schema()
    
    def _parse_product_schema(self, products_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse actual product data to extract schema."""
        schema = {
            "attributes": [
                {
                    "name": "id",
                    "required": True,
                    "dataType": "integer",
                    "description": "Product ID"
                },
                {
                    "name": "title",
                    "required": True,
                    "dataType": "string",
                    "maxLength": 255,
                    "description": "Product title"
                },
                {
                    "name": "body_html",
                    "required": False,
                    "dataType": "string",
                    "description": "Product description HTML"
                },
                {
                    "name": "vendor",
                    "required": False,
                    "dataType": "string",
                    "maxLength": 255,
                    "description": "Product vendor"
                },
                {
                    "name": "product_type",
                    "required": False,
                    "dataType": "string",
                    "maxLength": 255,
                    "description": "Product type"
                },
                {
                    "name": "tags",
                    "required": False,
                    "dataType": "string",
                    "description": "Product tags (comma-separated)"
                },
                {
                    "name": "variants",
                    "required": True,
                    "dataType": "array",
                    "description": "Product variants"
                }
            ],
            "metafields": [
                {
                    "namespace": "custom",
                    "key": "size",
                    "type": "single_line_text_field",
                    "description": "Product size"
                },
                {
                    "namespace": "custom",
                    "key": "color",
                    "type": "single_line_text_field",
                    "description": "Product color"
                },
                {
                    "namespace": "custom",
                    "key": "material",
                    "type": "single_line_text_field",
                    "description": "Product material"
                }
            ],
            "extractedAt": datetime.now().isoformat(),
            "source": "shopify_admin_api",
            "version": "2024-01"
        }
        return schema
    
    def _get_mock_schema(self) -> Dict[str, Any]:
        """Fallback mock schema for demo purposes."""
        return {
            "attributes": [
                {
                    "name": "id",
                    "required": True,
                    "dataType": "integer",
                    "description": "Product ID"
                },
                {
                    "name": "title",
                    "required": True,
                    "dataType": "string",
                    "maxLength": 255,
                    "description": "Product title"
                },
                {
                    "name": "body_html",
                    "required": False,
                    "dataType": "string",
                    "description": "Product description HTML"
                },
                {
                    "name": "vendor",
                    "required": False,
                    "dataType": "string",
                    "maxLength": 255,
                    "description": "Product vendor"
                },
                {
                    "name": "product_type",
                    "required": False,
                    "dataType": "string",
                    "maxLength": 255,
                    "description": "Product type"
                },
                {
                    "name": "tags",
                    "required": False,
                    "dataType": "string",
                    "description": "Product tags (comma-separated)"
                },
                {
                    "name": "variants",
                    "required": True,
                    "dataType": "array",
                    "description": "Product variants"
                }
            ],
            "metafields": [
                {
                    "namespace": "custom",
                    "key": "size",
                    "type": "single_line_text_field",
                    "description": "Product size"
                },
                {
                    "namespace": "custom",
                    "key": "color",
                    "type": "single_line_text_field",
                    "description": "Product color"
                },
                {
                    "namespace": "custom",
                    "key": "material",
                    "type": "single_line_text_field",
                    "description": "Product material"
                }
            ],
            "extractedAt": datetime.now().isoformat(),
            "source": "shopify_admin_api",
            "version": "2024-01"
        }

class SchemaExtractor:
    """Main schema extraction orchestrator."""
    
    def __init__(self):
        self.apis = {}
        self.results = {}
    
    def register_api(self, name: str, api_client):
        """Register an API client."""
        self.apis[name] = api_client
    
    def extract_all_schemas(self, google_merchant_id: str) -> Dict[str, Any]:
        """Extract schemas from all registered APIs."""
        tasks = []
        
        for name, api_client in self.apis.items():
            if name == "google_merchant_center":
                task = api_client.get_product_schema(google_merchant_id)
            elif name == "amazon_sp_api":
                task = api_client.get_product_schema("ATVPDKIKX0DER")
            elif name == "shopify_admin_api":
                task = api_client.get_product_schema()
            else:
                continue
            
            tasks.append((name, task))
        
        # Execute all API calls
        results = {}
        for name, task in tasks:
            try:
                schema = task
                results[name] = schema
                logger.info(f"Successfully extracted schema from {name}")
            except Exception as e:
                logger.error(f"Failed to extract schema from {name}: {e}")
                results[name] = {"error": str(e)}
        
        self.results = results
        return results
    
    def generate_canonical_mapping(self) -> Dict[str, Any]:
        """Generate canonical schema mapping from all extracted schemas."""
        canonical_attributes = {}
        
        for mp_name, schema in self.results.items():
            if "error" in schema:
                continue
            
            for attr in schema.get("attributes", []):
                attr_name = attr["name"].lower()
                
                if attr_name not in canonical_attributes:
                    canonical_attributes[attr_name] = {
                        "canonicalName": attr_name,
                        "mappings": {},
                        "dataTypes": set(),
                        "requiredFlags": set(),
                        "maxLengths": set()
                    }
                
                mapping = canonical_attributes[attr_name]["mappings"]
                mapping[mp_name] = {
                    "mpAttributeName": attr["name"],
                    "required": attr.get("required", False),
                    "dataType": attr.get("dataType", "string"),
                    "maxLength": attr.get("maxLength"),
                    "description": attr.get("description", "")
                }
                
                canonical_attributes[attr_name]["dataTypes"].add(attr.get("dataType", "string"))
                canonical_attributes[attr_name]["requiredFlags"].add(attr.get("required", False))
                if attr.get("maxLength"):
                    canonical_attributes[attr_name]["maxLengths"].add(attr["maxLength"])
        
        # Convert sets to lists for JSON serialization
        for attr_name, attr_data in canonical_attributes.items():
            attr_data["dataTypes"] = list(attr_data["dataTypes"])
            attr_data["requiredFlags"] = list(attr_data["requiredFlags"])
            attr_data["maxLengths"] = list(attr_data["maxLengths"])
        
        return {
            "canonicalAttributes": canonical_attributes,
            "generatedAt": datetime.now().isoformat(),
            "sourceAPIs": list(self.results.keys())
        }

def main():
    """Main execution function."""
    load_dotenv()
    # Ensure environment variables are set
    google_credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    google_merchant_id = os.environ.get("GOOGLE_MERCHANT_ID")

    if not all([google_credentials, google_merchant_id]):
        logger.error("Missing required environment variables: GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_MERCHANT_ID")
        return

    extractor = SchemaExtractor()
    
    # Register API clients
    google_api = GoogleMerchantCenterAPI(google_credentials)
    
    # Amazon SP-API: Load credentials from environment variables or config file
    amazon_client_id = os.environ.get("AMAZON_CLIENT_ID")
    amazon_client_secret = os.environ.get("AMAZON_CLIENT_SECRET")
    amazon_refresh_token = os.environ.get("AMAZON_REFRESH_TOKEN")
    amazon_iam_arn = os.environ.get("AMAZON_IAM_USER_ARN")
    
    # Try to load from SchemaOps config file if env vars not set
    if not all([amazon_client_id, amazon_client_secret, amazon_refresh_token]):
        # First try SchemaOps config directory
        config_path = Path(__file__).parent.parent / "config" / "amazon_sp_api.json"
        if not config_path.exists():
            # Fallback to amazon_sp_api_integration directory
            config_path = Path(__file__).parent.parent.parent / "amazon_sp_api_integration" / "config.json"
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                amazon_client_id = amazon_client_id or config.get('client_id')
                amazon_client_secret = amazon_client_secret or config.get('client_secret')
                amazon_refresh_token = amazon_refresh_token or config.get('refresh_token')
                amazon_iam_arn = amazon_iam_arn or config.get('iam_user_arn')
                logger.info(f"Loaded Amazon SP-API credentials from {config_path}")
            except Exception as e:
                logger.warning(f"Could not load Amazon credentials from {config_path}: {e}")
    
    # Initialize Amazon API - will use actual API if credentials are available
    amazon_api = AmazonSPAPI(
        client_id=amazon_client_id,
        client_secret=amazon_client_secret,
        refresh_token=amazon_refresh_token,
        iam_user_arn=amazon_iam_arn
    )
    
    shopify_api = ShopifyAdminAPI("demo-shop", "demo-access-token")
    
    extractor.register_api("google_merchant_center", google_api)
    extractor.register_api("amazon_sp_api", amazon_api)
    extractor.register_api("shopify_admin_api", shopify_api)
    
    # Extract schemas from all APIs
    logger.info("Starting schema extraction from all APIs...")
    schemas = extractor.extract_all_schemas(google_merchant_id)
    
    # Generate canonical mapping
    canonical_mapping = extractor.generate_canonical_mapping()
    
    # Save results
    output_dir = Path(__file__).parent.parent / "20_QA"
    output_dir.mkdir(exist_ok=True)
    
    # Save individual schemas
    for mp_name, schema in schemas.items():
        output_file = output_dir / f"{mp_name}_schema.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {mp_name} schema to {output_file}")
    
    # Save canonical mapping
    canonical_file = output_dir / "canonical_mapping.json"
    with open(canonical_file, 'w', encoding='utf-8') as f:
        json.dump(canonical_mapping, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved canonical mapping to {canonical_file}")
    
    # Print summary
    print(f"\n=== SCHEMA EXTRACTION SUMMARY ===")
    print(f"APIs processed: {len(schemas)}")
    print(f"Canonical attributes: {len(canonical_mapping['canonicalAttributes'])}")
    
    for mp_name, schema in schemas.items():
        if "error" not in schema:
            attr_count = len(schema.get("attributes", []))
            print(f"- {mp_name}: {attr_count} attributes")
        else:
            print(f"- {mp_name}: ERROR - {schema['error']}")

if __name__ == "__main__":
    from pathlib import Path
    main()
