#!/usr/bin/env python3
"""
Determination engine for marketplace compliance (TRAM Reasoning step).
Produces structured proposal: listable, restrictions, display requirements + reasoning + citations.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional


def load_feedback(feedback_path: Path, marketplace: str, category: str) -> List[Dict[str, Any]]:
    """Load past expert feedback for same marketplace x category."""
    if not feedback_path.exists():
        return []
    with open(feedback_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data if isinstance(data, list) else data.get("feedback", [])
    return [
        x for x in items
        if x.get("marketplace") == marketplace and x.get("category") == category
    ]


def build_context(sections: List[Dict], feedback: List[Dict]) -> str:
    """Build context string for LLM from retrieved sections and feedback."""
    ctx_parts = ["## Retrieved policy sections\n"]
    for i, s in enumerate(sections[:15], 1):
        ctx_parts.append(f"### Section {i} (source: {s.get('parentDoc', '')})\n{s.get('text', '')[:1500]}\n")
    if feedback:
        ctx_parts.append("\n## Past expert corrections (avoid repeating)\n")
        for f in feedback[-5:]:
            ctx_parts.append(f"- {f.get('reason', '')}\n")
    return "\n".join(ctx_parts)


def llm_determine(
    task: str,
    category: str,
    marketplace: str,
    context: str,
) -> Dict[str, Any]:
    """
    Call LLM for determination. Placeholder: returns mock structure.
    Wire to OpenAI/Anthropic for production.
    """
    # Placeholder response - replace with actual LLM call
    return {
        "listable": True,
        "restrictions": ["Verify product category matches marketplace taxonomy"],
        "displayRequirements": ["title", "brand", "image", "price"],
        "reasoningSummary": f"Based on {marketplace} policy sections, category '{category}' is generally listable. Standard display requirements apply.",
        "citations": [
            {"chunkId": "cite_1", "excerpt": "Products must include title, brand, and image."},
        ],
        "confidence": 0.85,
    }


def run_determination(
    task: str,
    category: str,
    marketplace: str,
    sections: List[Dict[str, Any]],
    feedback_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Main entry: produce determination proposal from retrieved sections.
    """
    feedback = load_feedback(feedback_path or Path(), marketplace, category)
    context = build_context(sections, feedback)
    proposal = llm_determine(task, category, marketplace, context)

    # Attach citation chunkIds from sections
    if sections:
        proposal["citations"] = [
            {"chunkId": s.get("chunkId", ""), "excerpt": s.get("text", "")[:200]}
            for s in sections[:5]
        ]

    return {
        "task": task,
        "category": category,
        "marketplace": marketplace,
        "proposal": proposal,
        "retrievedSectionCount": len(sections),
        "feedbackSignalsUsed": len(feedback),
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def main():
    """CLI: run determination from retrieval output."""
    import sys

    if len(sys.argv) < 5:
        print("Usage: determination_engine.py <sections_json> <task> <category> <marketplace> [feedback_path]")
        sys.exit(1)

    sections_path = Path(sys.argv[1])
    task = sys.argv[2]
    category = sys.argv[3]
    marketplace = sys.argv[4]
    feedback_path = Path(sys.argv[5]) if len(sys.argv) > 5 else None

    if not sections_path.exists():
        print(f"File not found: {sections_path}")
        sys.exit(1)

    with open(sections_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    sections = data.get("sections", data) if isinstance(data, dict) else data

    result = run_determination(task, category, marketplace, sections, feedback_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
