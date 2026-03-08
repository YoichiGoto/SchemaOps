#!/usr/bin/env python3
"""
Policy/regulation crawler for marketplace compliance (TRAM Ingestion step).
Fetches HTML/PDF/xlsx from Sources_Registry URLs and saves snapshots to 30_Archive.
"""
import csv
import sys
import hashlib
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

import requests

# Configure
REQUESTS_HEADERS = {
    "User-Agent": "SchemaOps-PolicyCrawler/1.0 (compliance monitoring; +https://github.com/schemaops)"
}
RATE_LIMIT_SECONDS = 2


def slugify(name: str) -> str:
    """Create filesystem-safe slug from source name."""
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "_", slug).strip("_")
    return slug[:50] if slug else "unknown"


def fetch_url(url: str, timeout: int = 30) -> Optional[bytes]:
    """Fetch URL content. Returns None on failure."""
    try:
        resp = requests.get(url, headers=REQUESTS_HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.content
    except requests.RequestException as e:
        return None


def content_hash(content: bytes) -> str:
    """MD5 hash of content for change detection."""
    return hashlib.md5(content).hexdigest()


def load_sources_registry(registry_path: Path) -> List[Dict[str, str]]:
    """Load Sources_Registry CSV."""
    rows = []
    with open(registry_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("url") and row.get("url").startswith("http"):
                rows.append(row)
    return rows


def crawl_sources(
    registry_path: Path,
    archive_base: Path,
    date_str: Optional[str] = None,
    skip_login_required: bool = True,
) -> List[Dict[str, Any]]:
    """
    Crawl all sources from registry and save snapshots.
    Returns list of crawl results with hash for change detection.
    """
    date_str = date_str or datetime.now().strftime("%Y%m%d")
    sources = load_sources_registry(registry_path)
    results = []

    for i, src in enumerate(sources):
        name = src.get("name", "unknown")
        url = src.get("url", "")
        doc_type = src.get("type", "html").lower()
        requires_login = (src.get("requiresLogin", "no") or "no").lower() in ("yes", "true", "1")

        if skip_login_required and requires_login:
            results.append({
                "name": name,
                "url": url,
                "status": "skipped",
                "reason": "requires_login",
                "hash": None,
            })
            continue

        if "example.com" in url:
            results.append({
                "name": name,
                "url": url,
                "status": "skipped",
                "reason": "example_url",
                "hash": None,
            })
            continue

        slug = slugify(name)
        archive_dir = archive_base / slug / date_str
        archive_dir.mkdir(parents=True, exist_ok=True)

        ext = {"html": "html", "pdf": "pdf", "xlsx": "xlsx"}.get(doc_type, "html")
        filename = f"snapshot.{ext}"
        filepath = archive_dir / filename

        content = fetch_url(url)
        if content is None:
            results.append({
                "name": name,
                "url": url,
                "status": "failed",
                "reason": "fetch_error",
                "hash": None,
            })
            continue

        filepath.write_bytes(content)
        doc_hash = content_hash(content)

        results.append({
            "name": name,
            "url": url,
            "status": "success",
            "path": str(filepath),
            "hash": doc_hash,
            "size_bytes": len(content),
        })

        if i < len(sources) - 1:
            time.sleep(RATE_LIMIT_SECONDS)

    return results


def report_to_change_monitor(results: List[Dict[str, Any]], monitor_dir: Path) -> int:
    """Report document hash changes to ChangeMonitor for determination_needs_review flags."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from change_monitor import ChangeMonitor

        monitor = ChangeMonitor(monitor_dir)
        count = 0
        for r in results:
            if r["status"] == "success" and r.get("hash"):
                changes = monitor.detect_document_changes(
                    r["name"], r["hash"], r.get("url", "")
                )
                if changes:
                    monitor.log_changes(r["name"], changes)
                    count += len(changes)
        return count
    except Exception:
        return 0


def main():
    """Run policy crawler."""
    script_dir = Path(__file__).resolve().parent
    root = script_dir.parent
    registry_path = root / "02_Templates" / "Sources_Registry.csv"
    archive_base = root / "30_Archive"
    monitor_dir = root / "20_QA" / "monitoring"

    if not registry_path.exists():
        print(f"Registry not found: {registry_path}")
        return 1

    print("Policy crawler: fetching sources from registry...")
    results = crawl_sources(registry_path, archive_base)

    success = sum(1 for r in results if r["status"] == "success")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = sum(1 for r in results if r["status"] == "failed")

    # Report document changes to change monitor
    reported = report_to_change_monitor(results, monitor_dir)
    if reported:
        print(f"  Reported {reported} document change(s) to change monitor (determination_needs_review)")

    print(f"\nResults: {success} success, {skipped} skipped, {failed} failed")
    for r in results:
        print(f"  - {r['name']}: {r['status']}" + (f" (hash={r.get('hash', '')[:8]}...)" if r.get("hash") else ""))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
