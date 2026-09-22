"""
graph/query.py — retrieve relevant subgraph context for a question.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _load_env() -> None:
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def get_driver():
    from neo4j import GraphDatabase
    _load_env()
    uri      = os.environ.get("NEO4J_URI",      "bolt://localhost:7687")
    username = os.environ.get("NEO4J_USERNAME",  "neo4j")
    password = os.environ.get("NEO4J_PASSWORD",  "swimple123")
    driver = GraphDatabase.driver(uri, auth=(username, password))
    driver.verify_connectivity()
    return driver


def _session_kwargs() -> dict:
    _load_env()
    db = os.environ.get("NEO4J_DATABASE") or None
    return {"database": db} if db else {}


# ---------- helpers ----------------------------------------------------------

_STOPWORDS = {
    "why", "what", "where", "how", "when", "who", "is", "are", "was",
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "at",
    "by", "do", "does", "did", "we", "our", "your", "my", "this", "that",
    "it", "be", "has", "have", "had", "not", "use", "used", "using",
}


def _search_terms(question: str) -> list[str]:
    words = [w.strip("?.!,;:\"'()") for w in question.lower().split()]
    return [w for w in words if len(w) > 2 and w not in _STOPWORDS]


def _node_to_text(node_data: dict) -> str:
    label = node_data.get("_label", "Node")
    name  = (
        node_data.get("name")
        or node_data.get("title")
        or node_data.get("path")
        or "?"
    )
    lines = [f"[{label}] {name}"]
    if node_data.get("rationale"):
        lines.append(f"  Rationale: {node_data['rationale']}")
    if node_data.get("type"):
        lines.append(f"  Type: {node_data['type']}")
    if node_data.get("file_path"):
        lines.append(f"  Path: {node_data['file_path']}")
    if node_data.get("category"):
        lines.append(f"  Category: {node_data['category']}")
    return "\n".join(lines)


def _format_record(record: dict) -> str:
    parts: list[str] = []
    node = record.get("n") or record.get("node")
    if node:
        node_dict = dict(node)
        node_dict["_label"] = list(node.labels)[0] if hasattr(node, "labels") else "Node"
        parts.append(_node_to_text(node_dict))

    rel_type = record.get("rel_type")
    neighbor = record.get("neighbor")
    if rel_type and neighbor:
        n = dict(neighbor)
        n_name = n.get("name") or n.get("title") or ""
        if n_name:
            parts.append(f"  -[{rel_type}]-> {n_name}")

    return "\n".join(parts)


# ---------- public API -------------------------------------------------------

def get_graph_context(question: str, driver) -> str:
    """Return a compact text block describing the subgraph most relevant to *question*."""
    terms = _search_terms(question)
    if not terms:
        return ""

    blocks: list[str] = []

    with driver.session(**_session_kwargs()) as session:
        # --- attempt full-text search (requires searchIndex from ingest) -----
        used_fulltext = False
        try:
            ft_query = " OR ".join(f'"{t}"' for t in terms[:4])
            rows = session.run(
                "CALL db.index.fulltext.queryNodes('searchIndex', $q) "
                "YIELD node, score "
                "WITH node, score ORDER BY score DESC LIMIT 10 "
                "OPTIONAL MATCH (node)-[r]-(nb) "
                "RETURN node, type(r) AS rel_type, nb AS neighbor, score",
                q=ft_query,
            ).data()

            for row in rows:
                raw_node = row.get("node")
                if raw_node is None:
                    continue
                nd = dict(raw_node)
                nd["_label"] = list(raw_node.labels)[0] if hasattr(raw_node, "labels") else "Node"
                block = _node_to_text(nd)
                rel_type = row.get("rel_type")
                neighbor = row.get("neighbor")
                if rel_type and neighbor:
                    n = dict(neighbor)
                    n_name = n.get("name") or n.get("title") or ""
                    if n_name:
                        block += f"\n  -[{rel_type}]-> {n_name}"
                blocks.append(block)
            used_fulltext = bool(blocks)
        except Exception:
            used_fulltext = False

        # --- fallback: simple CONTAINS keyword search ------------------------
        if not used_fulltext:
            for term in terms[:3]:
                rows = session.run(
                    "MATCH (n) "
                    "WHERE toLower(coalesce(n.name,''))      CONTAINS $t "
                    "   OR toLower(coalesce(n.title,''))     CONTAINS $t "
                    "   OR toLower(coalesce(n.rationale,'')) CONTAINS $t "
                    "WITH n LIMIT 6 "
                    "OPTIONAL MATCH (n)-[r]-(nb) "
                    "RETURN n, type(r) AS rel_type, nb AS neighbor",
                    t=term,
                ).data()

                for row in rows:
                    blocks.append(_format_record(row))

    # De-duplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for b in blocks:
        if b not in seen:
            seen.add(b)
            unique.append(b)

    return "\n\n".join(unique[:14])
