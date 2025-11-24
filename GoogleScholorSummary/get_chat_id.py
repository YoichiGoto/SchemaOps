import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

LARK_APP_ID = os.getenv("LARK_APP_ID")
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET")

def get_lark_token(app_id, app_secret):
    """Lark (Feishu) のTenant Access Tokenを取得する"""
    url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
    headers = {
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {
        "app_id": app_id,
        "app_secret": app_secret
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            print(f"Failed to get token: {data.get('msg')}")
            return None
        return data.get("tenant_access_token")
    except Exception as e:
        print(f"Error getting Lark token: {e}")
        return None

def list_chats(app_id, app_secret):
    """Botが参加しているチャットグループの一覧を取得する"""
    token = get_lark_token(app_id, app_secret)
    if not token:
        return

    url = "https://open.larksuite.com/open-apis/im/v1/chats"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    params = {
        "page_size": 20  # 必要に応じて増やす
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 0:
            items = data.get("data", {}).get("items", [])
            print("\n=== Chat List ===")
            found = False
            for item in items:
                print(f"Name: {item.get('name')}, Chat ID: {item.get('chat_id')}")
                if item.get('name') == "Google Scholar Summary":
                    print(f"\n✅ Found Target Group! -> Chat ID: {item.get('chat_id')}")
                    found = True
            if not found:
                print("\n⚠️ 'Google Scholar Summary' group not found. Please ensure the bot is added to the group.")
        else:
            print(f"Failed to list chats: {data}")

    except Exception as e:
        print(f"Error listing chats: {e}")

if __name__ == "__main__":
    if not LARK_APP_ID or not LARK_APP_SECRET:
        print("Error: Please set LARK_APP_ID and LARK_APP_SECRET in .env file or environment variables.")
    else:
        list_chats(LARK_APP_ID, LARK_APP_SECRET)

