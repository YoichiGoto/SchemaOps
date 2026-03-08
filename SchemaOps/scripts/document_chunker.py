#!/usr/bin/env python3
"""
Semantic document chunker for marketplace policy/regulation (TRAM Normalization step).
Splits documents into meaningful sections with metadata. Rule-based + optional LLM fallback.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

# Rule-based section patterns: heading-like, numbered sections, structural markers
SECTION_PATTERNS = [
    (r"^#{1,6}\s+.+$", "markdown_h"),
    (r"^<h[1-6][^>]*>.+</h[1-6]>", "html_h"),
    (r"^§\s*\d+(\.\d+)*\s", "section_mark"),
    (r"(?i)^Article\s+\d+", "article"),
    (r"^第\s*\d+\s*条", "japanese_article"),
    (r"^\d+(\.\d+)*\.\s+[A-Z]", "numbered"),
    (r"^\(\d+\)\s+", "paren_num"),
    (r"^[IVX]+\.\s+", "roman"),
]


def strip_html(html: str) -> str:
    """Remove HTML tags, preserve structure hints."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_html_sections(html: str) -> List[Dict[str, str]]:
    """Extract sections from HTML using tag structure."""
    sections = []
    # Match h1-h6 and their content until next h or end
    pattern = r"<(h[1-6])[^>]*>(.*?)</\1>"
    for m in re.finditer(pattern, html, re.DOTALL | re.I):
        level = int(m.group(1)[1])
        title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if title:
            sections.append({"title": title, "level": level, "type": "heading"})
    return sections


def rule_based_split(text: str, max_chunk_chars: int = 2000) -> List[Dict[str, Any]]:
    """
    Split text into semantic chunks using structural markers.
    Returns list of chunks with start/end positions and inferred boundaries.
    """
    lines = text.split("\n")
    chunks = []
    current = []
    current_len = 0
    last_boundary = 0

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            if current:
                current.append("")
            continue

        is_boundary = False
        for pat, _ in SECTION_PATTERNS:
            if re.match(pat, line_stripped):
                is_boundary = True
                break

        if is_boundary and current and current_len > 100:
            chunk_text = "\n".join(current).strip()
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "start_line": last_boundary,
                    "end_line": i,
                    "method": "rule_based",
                })
            current = [line_stripped]
            current_len = len(line_stripped)
            last_boundary = i
        else:
            current.append(line_stripped)
            current_len += len(line_stripped) + 1
            if current_len >= max_chunk_chars and current:
                chunk_text = "\n".join(current).strip()
                if chunk_text:
                    chunks.append({
                        "text": chunk_text,
                        "start_line": last_boundary,
                        "end_line": i,
                        "method": "rule_based",
                    })
                current = []
                current_len = 0
                last_boundary = i + 1

    if current:
        chunk_text = "\n".join(current).strip()
        if chunk_text:
            chunks.append({
                "text": chunk_text,
                "start_line": last_boundary,
                "end_line": len(lines),
                "method": "rule_based",
            })

    return chunks if chunks else [{"text": text[:max_chunk_chars], "start_line": 0, "end_line": len(lines), "method": "rule_based"}]


def llm_split_fallback(text: str, doc_path: str) -> List[Dict[str, Any]]:
    """
    LLM-based fallback for documents that don't fit rule patterns.
    Placeholder: returns rule_based_split result. Wire to actual LLM for document-specific rules.
    """
    return rule_based_split(text)


def add_metadata(
    chunks: List[Dict[str, Any]],
    parent_doc: str,
    marketplace: str,
    effective_date: Optional[str] = None,
    policy_type: str = "guideline",
    hierarchy: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Enrich chunks with metadata."""
    hierarchy = hierarchy or []
    result = []
    for i, c in enumerate(chunks):
        chunk = dict(c)
        chunk["parentDoc"] = parent_doc
        chunk["marketplace"] = marketplace
        chunk["effectiveDate"] = effective_date
        chunk["policyType"] = policy_type
        chunk["hierarchy"] = hierarchy + [f"chunk_{i}"]
        chunk["chunkId"] = f"{marketplace}_{parent_doc}_{i}".replace(" ", "_").replace("/", "_")
        result.append(chunk)
    return result


def chunk_document(
    content: str,
    content_type: str,
    parent_doc: str,
    marketplace: str,
    effective_date: Optional[str] = None,
    policy_type: str = "guideline",
    use_llm_fallback: bool = False,
) -> List[Dict[str, Any]]:
    """
    Main entry: chunk document and add metadata.
    content_type: 'html' | 'text'
    """
    if content_type == "html":
        text = strip_html(content)
    else:
        text = content

    chunks = rule_based_split(text)
    if use_llm_fallback and len(chunks) <= 1 and len(text) > 500:
        chunks = llm_split_fallback(text, parent_doc)

    return add_metadata(
        chunks,
        parent_doc=parent_doc,
        marketplace=marketplace,
        effective_date=effective_date,
        policy_type=policy_type,
    )


def chunk_file(
    file_path: Path,
    marketplace: str,
    effective_date: Optional[str] = None,
    policy_type: str = "guideline",
) -> List[Dict[str, Any]]:
    """Chunk a file from disk."""
    suffix = file_path.suffix.lower()
    if suffix == ".html":
        content = file_path.read_text(encoding="utf-8", errors="replace")
        content_type = "html"
    else:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        content_type = "text"

    parent_doc = file_path.stem
    return chunk_document(
        content,
        content_type,
        parent_doc=parent_doc,
        marketplace=marketplace,
        effective_date=effective_date,
        policy_type=policy_type,
    )


def main():
    """CLI: chunk a document file."""
    import sys

    if len(sys.argv) < 4:
        print("Usage: document_chunker.py <file_path> <marketplace> <output_json> [policyType]")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    marketplace = sys.argv[2]
    output_path = Path(sys.argv[3])
    policy_type = sys.argv[4] if len(sys.argv) > 4 else "guideline"

    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    chunks = chunk_file(file_path, marketplace, policy_type=policy_type)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "chunks": chunks,
        "source": str(file_path),
        "marketplace": marketplace,
        "chunkedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Chunked into {len(chunks)} sections, saved to {output_path}")


if __name__ == "__main__":
    main()
