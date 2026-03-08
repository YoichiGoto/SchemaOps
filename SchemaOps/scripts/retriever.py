#!/usr/bin/env python3
"""
Task-oriented hybrid retrieval for policy chunks (TRAM Retrieval step).
Filter by marketplace, hybrid search, merge, rerank, expand context.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional


def _extract_keywords(text: str, min_len: int = 2) -> List[str]:
    """Extract keywords for sparse search."""
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return [t for t in text.split() if len(t) >= min_len]


CHROMA_AVAILABLE = False
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    pass


def sparse_search(
    query: str,
    sparse_index: Dict[str, List[str]],
    chunks_by_id: Dict[str, Dict],
    marketplace: Optional[str] = None,
    n: int = 20,
) -> List[Dict[str, Any]]:
    """Keyword-based sparse search."""
    qwords = set(_extract_keywords(query))
    scores = {}
    for w in qwords:
        for cid in sparse_index.get(w, []):
            chunk = chunks_by_id.get(cid)
            if chunk and (marketplace is None or chunk.get("marketplace") == marketplace):
                scores[cid] = scores.get(cid, 0) + 1

    ranked = sorted(scores.items(), key=lambda x: -x[1])[:n]
    return [{"chunkId": cid, "score": s, "chunk": chunks_by_id.get(cid)} for cid, s in ranked]


def dense_search(
    query: str,
    index_dir: Path,
    marketplace: Optional[str] = None,
    n: int = 20,
) -> List[Dict[str, Any]]:
    """Dense vector search via ChromaDB."""
    if not CHROMA_AVAILABLE:
        return []

    client = chromadb.PersistentClient(
        path=str(index_dir / "chroma_db"),
        settings=Settings(anonymized_telemetry=False),
    )
    coll = client.get_or_create_collection("schemaops_policy")
    where = {"marketplace": marketplace} if marketplace else None
    results = coll.query(query_texts=[query], n_results=n, where=where)
    if not results or not results["ids"]:
        return []

    chunks_path = index_dir / "chunks.json"
    chunks_by_id = {}
    if chunks_path.exists():
        with open(chunks_path, "r", encoding="utf-8") as f:
            for c in json.load(f):
                chunks_by_id[c.get("chunkId", "")] = c

    out = []
    for i, cid in enumerate(results["ids"][0]):
        dist = results["distances"][0][i] if results.get("distances") else 0
        out.append({"chunkId": cid, "score": 1 - dist, "chunk": chunks_by_id.get(cid)})
    return out


def merge_and_boost(dense_results: List, sparse_results: List) -> List[Dict[str, Any]]:
    """Merge results; boost chunks that appear in both."""
    seen = {}
    for r in dense_results:
        cid = r.get("chunkId", "")
        seen[cid] = {"chunkId": cid, "dense_score": r.get("score", 0), "sparse_score": 0, "chunk": r.get("chunk")}
    for r in sparse_results:
        cid = r.get("chunkId", "")
        if cid in seen:
            seen[cid]["sparse_score"] = r.get("score", 0)
            seen[cid]["boost"] = True
        else:
            seen[cid] = {"chunkId": cid, "dense_score": 0, "sparse_score": r.get("score", 0), "chunk": r.get("chunk"), "boost": False}

    combined = []
    for v in seen.values():
        s = v["dense_score"] + v["sparse_score"]
        if v.get("boost"):
            s *= 1.5
        v["combined_score"] = s
        combined.append(v)
    return sorted(combined, key=lambda x: -x["combined_score"])


def get_adjacent_chunks(chunk_id: str, chunks: List[Dict], chunks_by_id: Dict) -> List[Dict]:
    """Get neighboring chunks from same parent document."""
    chunk = chunks_by_id.get(chunk_id)
    if not chunk:
        return []
    parent = chunk.get("parentDoc", "")
    marketplace = chunk.get("marketplace", "")
    same_doc = [c for c in chunks if c.get("parentDoc") == parent and c.get("marketplace") == marketplace]
    same_doc.sort(key=lambda c: c.get("start_line", 0))
    idx = next((i for i, c in enumerate(same_doc) if c.get("chunkId") == chunk_id), -1)
    if idx < 0:
        return []
    adj = []
    if idx > 0:
        adj.append(same_doc[idx - 1])
    if idx < len(same_doc) - 1:
        adj.append(same_doc[idx + 1])
    return adj


def retrieve(
    query: str,
    index_dir: Path,
    marketplace: Optional[str] = None,
    n_initial: int = 20,
    n_final: int = 10,
    expand_context: bool = True,
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieve: filter, search, merge, rerank, optionally expand.
    Returns curated section set for Reasoning step.
    """
    with open(index_dir / "chunks.json", "r", encoding="utf-8") as f:
        chunks = json.load(f)
    chunks_by_id = {c.get("chunkId", ""): c for c in chunks}

    with open(index_dir / "sparse_index.json", "r", encoding="utf-8") as f:
        sparse_index = json.load(f)

    dense_res = dense_search(query, index_dir, marketplace, n_initial)
    sparse_res = sparse_search(query, sparse_index, chunks_by_id, marketplace, n_initial)

    merged = merge_and_boost(dense_res, sparse_res)
    top = merged[:n_final]

    result = []
    for m in top:
        c = m.get("chunk")
        if c:
            entry = dict(c)
            entry["retrieval_score"] = m.get("combined_score", 0)
            result.append(entry)
            if expand_context:
                for adj in get_adjacent_chunks(m["chunkId"], chunks, chunks_by_id):
                    if adj.get("chunkId") not in [x.get("chunkId") for x in result]:
                        adj_copy = dict(adj)
                        adj_copy["retrieval_score"] = 0
                        adj_copy["adjacent"] = True
                        result.append(adj_copy)

    return result[:n_final * 2] if expand_context else result


def main():
    """CLI: run retrieval."""
    import sys

    if len(sys.argv) < 4:
        print("Usage: retriever.py <index_dir> <query> <marketplace> [--no-expand]")
        sys.exit(1)

    index_dir = Path(sys.argv[1])
    query = sys.argv[2]
    marketplace = sys.argv[3]
    expand = "--no-expand" not in sys.argv

    if not (index_dir / "chunks.json").exists():
        print(f"Index not found: {index_dir}")
        sys.exit(1)

    results = retrieve(query, index_dir, marketplace=marketplace, expand_context=expand)
    print(json.dumps({"query": query, "marketplace": marketplace, "sections": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
