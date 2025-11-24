import os
import time
import hashlib
from dotenv import load_dotenv
from utils import (
    load_config, load_history, save_history, search_scholar,
    download_pdf, GeminiProcessor, send_lark_notification
)

# Load environment variables (for local testing)
load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LARK_APP_ID = os.getenv("LARK_APP_ID")
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET")
LARK_CHAT_ID = os.getenv("LARK_CHAT_ID")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "dummy/repo") # defaults for local test
GITHUB_REF_NAME = os.getenv("GITHUB_REF_NAME", "main")

def get_safe_filename(title):
    """タイトルからファイル名に使用できる文字列を生成"""
    keepcharacters = (' ','.','_')
    return "".join(c for c in title if c.isalnum() or c in keepcharacters).rstrip().replace(' ', '_')[:50] + ".pdf"

def main():
    if not all([SERPAPI_KEY, GEMINI_API_KEY, LARK_APP_ID, LARK_APP_SECRET, LARK_CHAT_ID]):
        print("Error: Missing API keys or Lark config (App ID/Secret/Chat ID).")
        return

    config = load_config()
    history = load_history()
    gemini = GeminiProcessor(GEMINI_API_KEY)
    
    new_history_entries = set()
    
    # Combine keywords and authors for search
    # Authors: "author:Yann LeCun"
    queries = config.get("keywords", []) + [f"author:\"{a}\"" for a in config.get("authors", [])]

    for query in queries:
        print(f"Searching for: {query}")
        try:
            results = search_scholar(query, SERPAPI_KEY)
        except Exception as e:
            print(f"Search failed for {query}: {e}")
            continue

        for result in results:
            title = result.get("title")
            result_id = result.get("result_id") # SerpApi ID or construct unique ID
            
            # IDがない場合はタイトルとリンクでハッシュを作る
            if not result_id:
                unique_str = title + result.get("link", "")
                result_id = hashlib.md5(unique_str.encode()).hexdigest()

            if result_id in history or result_id in new_history_entries:
                print(f"Skipping known article: {title}")
                continue

            # PDFリンクのチェック
            pdf_url = None
            if "resources" in result:
                for resource in result["resources"]:
                    if resource.get("file_format") == "PDF":
                        pdf_url = resource.get("link")
                        break
            
            # トップレベルのlinkがPDFの場合も考慮（稀だが）
            if not pdf_url and result.get("link", "").lower().endswith(".pdf"):
                pdf_url = result.get("link")

            if not pdf_url:
                print(f"No PDF found for: {title}")
                continue

            print(f"Processing: {title}")
            
            # Ensure directory exists
            os.makedirs("data/pdfs", exist_ok=True)

            # Download PDF
            filename = f"{result_id}_{get_safe_filename(title)}"
            save_path = os.path.join("data/pdfs", filename)
            
            if download_pdf(pdf_url, save_path):
                try:
                    # Upload to Gemini
                    file_obj = gemini.upload_file(save_path)
                    
                    # Analyze
                    print("Waiting for Gemini analysis...")
                    analysis_result = gemini.analyze_paper(file_obj)
                    
                    # Construct GitHub URL
                    # Assuming public repo or user has access
                    github_pdf_url = f"https://github.com/{GITHUB_REPOSITORY}/blob/{GITHUB_REF_NAME}/data/pdfs/{filename}"
                    
                    # Publication info
                    pub_info = result.get("publication_info", {}).get("summary", "N/A")
                    
                    # Send Notification
                    message_data = {
                        "title": title,
                        "authors": pub_info, # Sometimes contains author names
                        "publication_info": pub_info,
                        "pdf_url": pdf_url,
                        "github_pdf_url": github_pdf_url,
                        "analysis_result": analysis_result
                    }
                    
                    send_lark_notification(LARK_APP_ID, LARK_APP_SECRET, LARK_CHAT_ID, message_data)
                    
                    # Mark as processed
                    new_history_entries.add(result_id)
                    
                    # Wait a bit to avoid rate limits
                    time.sleep(5)
                    
                except Exception as e:
                    print(f"Error processing {title}: {e}")
            else:
                print("Download failed.")

    # Update history
    if new_history_entries:
        history.update(new_history_entries)
        save_history(history)
        print(f"Updated history with {len(new_history_entries)} new entries.")
    else:
        print("No new articles found.")

if __name__ == "__main__":
    main()
