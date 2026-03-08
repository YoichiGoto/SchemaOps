#!/usr/bin/env python3
"""
Hybrid indexer for policy chunks (TRAM Indexing step).
Dense (embedding) + Sparse (keyword) indexing with metadata filters.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

CHROMA_AVAILABLE = False
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    pass


def extract_keywords(text: str, min_len: int = 2) -> List[str]:
    """Extract keywords for sparse indexing (simple tokenization)."""
    text = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = text.split()
    return [t for t in tokens if len(t) >= min_len]


def build_sparse_index(chunks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Build keyword -> chunkIds mapping for sparse retrieval."""
    index = {}
    for chunk in chunks:
        cid = chunk.get("chunkId", "")
        text = chunk.get("text", "")
        for kw in set(extract_keywords(text)):
            index.setdefault(kw, []).append(cid)
    return index


def save_sparse_index(index: Dict[str, List[str]], chunks: List[Dict[str, Any]], out_dir: Path):
    """Save sparse index and chunks to JSON."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "sparse_index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)
    with open(out_dir / "chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)


def load_chunks_from_file(path: Path) -> List[Dict[str, Any]]:
    """Load chunks from document_chunker output JSON."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("chunks", data) if isinstance(data, dict) else data


class HybridIndexer:
    """Dense + Sparse hybrid indexer for policy chunks."""

    def __init__(self, index_dir: Path, collection_name: str = "schemaops_policy"):
        self.index_dir = index_dir
        self.collection_name = collection_name
        self.chroma_client = None
        self.collection = None
        self.sparse_index = {}
        self.chunks_by_id = {}

        if CHROMA_AVAILABLE:
            self.chroma_client = chromadb.PersistentClient(
                path=str(index_dir / "chroma_db"),
                settings=Settings(anonymized_telemetry=False),
            )
            self.collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "SchemaOps policy chunks"},
            )

    def index_chunks(self, chunks: List[Dict[str, Any]], reset: bool = False):
        """Index chunks in both dense and sparse."""
        if CHROMA_AVAILABLE and self.collection and reset:
            try:
                self.chroma_client.delete_collection(self.collection_name)
            except Exception:
                pass
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "SchemaOps policy chunks"},
            )

        ids = []
        documents = []
        metadatas = []

        for c in chunks:
            cid = c.get("chunkId", f"chunk_{len(ids)}")
            ids.append(cid)
            documents.append(c.get("text", ""))
            meta = {
                "marketplace": c.get("marketplace", ""),
                "policyType": c.get("policyType", "guideline"),
                "effectiveDate": c.get("effectiveDate") or "",
                "parentDoc": c.get("parentDoc", ""),
            }
            metadatas.append(meta)
            self.chunks_by_id[cid] = c

        if CHROMA_AVAILABLE and self.collection and documents:
            self.collection.add(ids=ids, documents=documents, metadatas=metadatas)

        self.sparse_index = build_sparse_index(chunks)
        save_sparse_index(self.sparse_index, chunks, self.index_dir)

    def index_from_file(self, chunks_path: Path, reset: bool = False):
        """Load chunks from file and index."""
        chunks = load_chunks_from_file(chunks_path)
        self.index_chunks(chunks, reset=reset)


def main():
    """CLI: index chunks from document_chunker output."""
    import sys

    if len(sys.argv) < 3:
        print("Usage: indexer.py <chunks_json> <index_dir> [--reset]")
        sys.exit(1)

    chunks_path = Path(sys.argv[1])
    index_dir = Path(sys.argv[2])
    reset = "--reset" in sys.argv

    if not chunks_path.exists():
        print(f"File not found: {chunks_path}")
        sys.exit(1)

    indexer = HybridIndexer(index_dir)
    indexer.index_from_file(chunks_path, reset=reset)

    n = len(indexer.chunks_by_id)
    print(f"Indexed {n} chunks to {index_dir}")
    if CHROMA_AVAILABLE:
        print("  Dense: ChromaDB")
    print("  Sparse: sparse_index.json")

if __name__ == "__main__":
    main()
