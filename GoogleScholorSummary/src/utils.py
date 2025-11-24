import os
import json
import requests
import time
from serpapi import GoogleSearch
import google.generativeai as genai
from datetime import datetime

def load_config():
    """config/targets.jsonを読み込む"""
    with open('config/targets.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def load_history():
    """data/history.jsonを読み込む"""
    try:
        with open('data/history.json', 'r', encoding='utf-8') as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_history(history_set):
    """data/history.jsonを保存する"""
    with open('data/history.json', 'w', encoding='utf-8') as f:
        json.dump(list(history_set), f, ensure_ascii=False, indent=2)

def search_scholar(query, api_key):
    """SerpApiを使ってGoogle Scholarを検索する"""
    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": api_key,
        "as_ylo": datetime.now().year, # 今年の論文に限定
        "hl": "ja", # 日本語UIでの結果（必要に応じて）
        "num": 10 # 取得件数
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    return results.get("organic_results", [])

def download_pdf(url, save_path):
    """PDFをダウンロードして保存する"""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Content-Typeチェック (簡易)
        content_type = response.headers.get('Content-Type', '').lower()
        if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
             # URLが.pdfで終わっている場合は続行してみる
            if not url.lower().endswith('.pdf'):
                print(f"Warning: Content-Type is {content_type}, not PDF. URL: {url}")
                return False

        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Failed to download PDF from {url}: {e}")
        return False

class GeminiProcessor:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def upload_file(self, path):
        """ファイルをGeminiにアップロードする"""
        print(f"Uploading file: {path}")
        sample_file = genai.upload_file(path=path)
        print(f"Uploaded file: {sample_file.display_name} as {sample_file.uri}")
        return sample_file

    def analyze_paper(self, file_obj):
        """論文のAbstract翻訳と詳細要約を生成する"""
        # 1. Abstract翻訳と全体の要約を一度に要求する（トークン節約・高速化）
        prompt = """
        あなたは優秀な研究アシスタントです。提供された論文PDFを読んで、以下の2つのタスクを実行してください。
        
        **タスク1: Abstractの和訳**
        論文のAbstract（概要）セクションを見つけ、それを自然な日本語に翻訳してください。
        
        **タスク2: 詳細要約**
        論文全体の内容を日本語で要約してください。以下の項目を含めてください：
        - 研究の背景と目的
        - 提案手法やアプローチの新規性
        - 実験結果や主な発見
        - 結論と今後の展望
        
        出力形式：
        ---
        ## Abstract和訳
        (ここに翻訳)
        
        ## 詳細要約
        (ここに要約)
        ---
        """
        response = self.model.generate_content([prompt, file_obj])
        return response.text

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

def send_lark_notification(app_id, app_secret, chat_id, message_data):
    """Lark Appを使用してメッセージを送信する"""
    token = get_lark_token(app_id, app_secret)
    if not token:
        print("Skipping notification due to missing token.")
        return

    url = "https://open.larksuite.com/open-apis/im/v1/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    # message_dataはタイトル、リンク、要約などを含む辞書
    card_content = {
        "config": {
            "wide_screen_mode": True
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "content": f"**著者:** {message_data['authors']}\n**Source:** {message_data['publication_info']}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "div",
                "text": {
                    "content": message_data['analysis_result'], # Geminiの出力（Markdown）
                    "tag": "lark_md"
                }
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "content": "オリジナルPDFを開く",
                            "tag": "plain_text"
                        },
                        "url": message_data['pdf_url'],
                        "type": "primary"
                    },
                     {
                        "tag": "button",
                        "text": {
                            "content": "GitHubでPDFを見る",
                            "tag": "plain_text"
                        },
                        "url": message_data['github_pdf_url'],
                        "type": "default"
                    }
                ]
            }
        ],
        "header": {
            "template": "blue",
            "title": {
                "content": f"📄 新着論文: {message_data['title']}",
                "tag": "plain_text"
            }
        }
    }

    # メッセージ送信APIのパラメータ
    # params receive_id_type=chat_id is needed in URL query
    params = {
        "receive_id_type": "chat_id"
    }
    
    payload = {
        "receive_id": chat_id,
        "msg_type": "interactive",
        "content": json.dumps(card_content) # API requires JSON string for 'content'
    }

    try:
        response = requests.post(url, params=params, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            print(f"Failed to send notification (API Error): {data}")
        else:
            print("Notification sent to Lark.")
    except Exception as e:
        print(f"Failed to send notification: {e}")
