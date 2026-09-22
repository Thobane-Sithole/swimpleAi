"""
graph/ingest.py — parse knowledge_base/ files with Claude, load entities into Neo4j.

Run once (or whenever docs change):
    python -m graph.ingest
"""

import json
import os
import sys
from pathlib import Path

import anthropic

KB_DIR = Path(__file__).parent.parent / "knowledge_base"

# ---------- env loader -------------------------------------------------------

def _load_env() -> None:
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# ---------- Claude client ----------------------------------------------------

def _make_client() -> anthropic.Anthropic:
    _load_env()
    workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
    headers = {"anthropic-workspace-id": workspace_id} if workspace_id else {}
    return anthropic.Anthropic(default_headers=headers)

# ---------- Neo4j driver -----------------------------------------------------

def _get_driver():
    from neo4j import GraphDatabase
    _load_env()
    uri      = os.environ.get("NEO4J_URI",      "bolt://localhost:7687")
    username = os.environ.get("NEO4J_USERNAME",  "neo4j")
    password = os.environ.get("NEO4J_PASSWORD",  "swimple123")
    return GraphDatabase.driver(uri, auth=(username, password))


def _db() -> str | None:
    """Return database name for AuraDB; None means use the driver default."""
    return os.environ.get("NEO4J_DATABASE") or None

# ---------- entity extraction prompt ----------------------------------------

_EXTRACTION_PROMPT = """\
You are a knowledge-graph extraction engine. Analyse the document below and return ONLY valid JSON — no prose, no markdown fences — with this exact shape:

{
  "components": [
    {"name": "<string>", "type": "service|module|function|file", "path": "<string or null>"}
  ],
  "technologies": [
    {"name": "<string>", "category": "database|cache|auth|framework|language|queue|other"}
  ],
  "decisions": [
    {"id": "<slug>", "title": "<string>", "rationale": "<string>", "date": "<string or null>"}
  ],
  "relationships": [
    {
      "from_name":  "<string>",
      "from_label": "Component|Technology|Decision",
      "to_name":    "<string>",
      "to_label":   "Component|Technology|Decision",
      "type":       "USES|DEPENDS_ON|CHOOSES|REJECTS|EXPLAINS|STORES_IN|ALTERNATIVE_TO"
    }
  ]
}

Rules:
- Only include entities explicitly present in the document.
- decision.id must be a short kebab-case slug unique within this document.
- For Decision nodes in relationships use the decision title, not the id.
- Keep names short and stable (e.g. "Auth Service", "PostgreSQL", "Store refresh tokens in Redis").

Document:
"""


def _extract_entities(content: str, client: anthropic.Anthropic) -> dict:
    resp = client.messages.create(
        model="claude-opus-5",
        max_tokens=2048,
        messages=[{"role": "user", "content": _EXTRACTION_PROMPT + content}],
    )
    raw = resp.content[0].text.strip()
    # Strip accidental markdown fences
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip() if len(parts) >= 2 else raw
    return json.loads(raw)

# ---------- schema setup -----------------------------------------------------

def _apply_schema(session) -> None:
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Component)  REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Technology)  REQUIRE t.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (doc:Document) REQUIRE doc.path IS UNIQUE",
    ]
    for q in constraints:
        session.run(q)

    # Full-text index across all searchable node properties
    try:
        session.run(
            "CREATE FULLTEXT INDEX searchIndex IF NOT EXISTS "
            "FOR (n:Component|Technology|Decision|Document) "
            "ON EACH [n.name, n.title, n.rationale, n.content]"
        )
    except Exception:
        pass  # Index may already exist or APOC not installed; fallback used in query.py

# ---------- graph loading helpers --------------------------------------------

def _upsert_nodes(session, entities: dict, doc_path: str) -> None:
    # Document node
    session.run(
        "MERGE (d:Document {path: $path}) SET d.name = $name",
        path=doc_path, name=Path(doc_path).name,
    )

    for c in entities.get("components", []):
        session.run(
            "MERGE (c:Component {name: $name}) "
            "SET c.type = $type, c.file_path = $file_path",
            name=c["name"], type=c.get("type", "unknown"), file_path=c.get("path") or "",
        )
        session.run(
            "MATCH (d:Document {path: $doc}), (c:Component {name: $name}) "
            "MERGE (d)-[:DESCRIBES]->(c)",
            doc=doc_path, name=c["name"],
        )

    for t in entities.get("technologies", []):
        session.run(
            "MERGE (t:Technology {name: $name}) SET t.category = $cat",
            name=t["name"], cat=t.get("category", "other"),
        )
        session.run(
            "MATCH (d:Document {path: $doc}), (t:Technology {name: $name}) "
            "MERGE (d)-[:MENTIONS]->(t)",
            doc=doc_path, name=t["name"],
        )

    for dec in entities.get("decisions", []):
        session.run(
            "MERGE (dec:Decision {title: $title}) "
            "SET dec.id = $id, dec.rationale = $rationale, dec.date = $date",
            id=dec["id"], title=dec["title"],
            rationale=dec.get("rationale", ""), date=dec.get("date") or "",
        )
        session.run(
            "MATCH (d:Document {path: $doc}), (dec:Decision {title: $title}) "
            "MERGE (d)-[:RECORDS]->(dec)",
            doc=doc_path, title=dec["title"],
        )


def _upsert_relationships(session, entities: dict) -> None:
    valid_rels = {"USES", "DEPENDS_ON", "CHOOSES", "REJECTS", "EXPLAINS", "STORES_IN", "ALTERNATIVE_TO"}
    valid_labels = {"Component", "Technology", "Decision"}

    for rel in entities.get("relationships", []):
        from_label = rel.get("from_label", "")
        to_label   = rel.get("to_label",   "")
        rel_type   = rel.get("type",        "")

        if from_label not in valid_labels or to_label not in valid_labels:
            continue
        if rel_type not in valid_rels:
            continue

        # Decision nodes are keyed by title; others by name
        from_prop = "title" if from_label == "Decision" else "name"
        to_prop   = "title" if to_label   == "Decision" else "name"

        cypher = (
            f"MATCH (a:{from_label} {{{from_prop}: $from_val}}), "
            f"      (b:{to_label}   {{{to_prop}:   $to_val}}) "
            f"MERGE (a)-[:{rel_type}]->(b)"
        )
        try:
            session.run(cypher, from_val=rel["from_name"], to_val=rel["to_name"])
        except Exception:
            pass  # Node may not exist yet; skip

# ---------- main ingest loop -------------------------------------------------

def ingest() -> None:
    _load_env()
    client = _make_client()
    driver = _get_driver()

    db = _db()
    session_kwargs = {"database": db} if db else {}

    with driver.session(**session_kwargs) as session:
        _apply_schema(session)

    files = [
        f for f in sorted(KB_DIR.rglob("*"))
        if f.is_file() and f.suffix in (".md", ".txt", ".json", ".yaml", ".py")
    ]

    if not files:
        print("No files found in knowledge_base/ — nothing to ingest.")
        driver.close()
        return

    print(f"Ingesting {len(files)} file(s) into Neo4j...")

    for fpath in files:
        print(f"  {fpath.name} ...", end=" ", flush=True)
        content = fpath.read_text(encoding="utf-8", errors="replace")
        rel_path = str(fpath.relative_to(KB_DIR.parent))

        try:
            entities = _extract_entities(content, client)
            with driver.session(**session_kwargs) as session:
                _upsert_nodes(session, entities, rel_path)
                _upsert_relationships(session, entities)
            n_c = len(entities.get("components",  []))
            n_t = len(entities.get("technologies", []))
            n_d = len(entities.get("decisions",   []))
            print(f"{n_c} components, {n_t} technologies, {n_d} decisions")
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
        except Exception as e:
            print(f"Error: {e}")

    driver.close()
    print("\nDone — knowledge graph is ready.")
    print("Open http://localhost:7474 to browse it.")


if __name__ == "__main__":
    ingest()
