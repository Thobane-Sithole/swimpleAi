"""
Why Swimple — asks "why" about your codebase.

Backed by a Neo4j knowledge graph when available; falls back to flat-file mode
so the agent keeps working even if Neo4j isn't running.

Usage:
    python why_oracle.py
    python -m why_oracle
"""

import os
import anthropic
from pathlib import Path

# ---------- load .env --------------------------------------------------------

_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ---------- constants --------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are Swimple's codebase onboarding engineer. "
    "Your job is to answer *why* questions — why certain patterns exist, "
    "why a technology was chosen, why a particular design was adopted. "
    "Answer ONLY from the knowledge context supplied; cite specific components, "
    "decisions, or technologies by name. "
    "If the question is not covered by the provided context, say so clearly "
    "rather than guessing."
)

KB_DIR = Path(__file__).parent / "knowledge_base"

# ---------- clients ----------------------------------------------------------

def _make_client() -> anthropic.Anthropic:
    workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
    headers = {"anthropic-workspace-id": workspace_id} if workspace_id else {}
    return anthropic.Anthropic(default_headers=headers)


def _try_neo4j_driver():
    """Return a live Neo4j driver, or None if Neo4j is unavailable."""
    try:
        from graph.query import get_driver
        return get_driver()
    except Exception:
        return None

# ---------- context retrieval ------------------------------------------------

def _flat_knowledge() -> str:
    """Read all files from knowledge_base/ as a single text block."""
    if not KB_DIR.exists():
        return ""
    parts: list[str] = []
    for path in sorted(KB_DIR.rglob("*")):
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                parts.append(f"=== {path.relative_to(KB_DIR)} ===\n{text}")
            except OSError:
                pass
    return "\n\n".join(parts)


def _get_context(question: str, driver) -> str:
    if driver is not None:
        try:
            from graph.query import get_graph_context
            ctx = get_graph_context(question, driver)
            if ctx:
                return f"--- KNOWLEDGE GRAPH ---\n{ctx}\n--- END GRAPH ---"
        except Exception as exc:
            print(f"[Neo4j query error — falling back to flat files: {exc}]")

    flat = _flat_knowledge()
    if flat:
        return f"--- KNOWLEDGE BASE ---\n{flat}\n--- END ---"
    return ""

# ---------- main loop --------------------------------------------------------

def run() -> None:
    client = _make_client()
    driver = _try_neo4j_driver()
    messages: list[dict] = []

    mode = "Neo4j knowledge graph" if driver else "flat-file mode (Neo4j not connected)"
    print(f"Why Oracle — {mode}")
    print("Type your question and press Enter. Type 'quit' to exit.\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if question.lower() in ("quit", "exit", "q"):
            break
        if not question:
            continue

        context = _get_context(question, driver)
        system = _SYSTEM_PROMPT + (f"\n\n{context}" if context else "")

        messages.append({"role": "user", "content": question})

        print("Oracle: ", end="", flush=True)
        response_text = ""
        with client.messages.stream(
            model="claude-opus-5",
            max_tokens=4096,
            system=system,
            messages=messages,
        ) as stream:
            for chunk in stream.text_stream:
                print(chunk, end="", flush=True)
                response_text += chunk
        print("\n")

        messages.append({"role": "assistant", "content": response_text})

    if driver:
        driver.close()


if __name__ == "__main__":
    run()
