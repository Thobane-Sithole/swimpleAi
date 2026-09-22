"""
Meeting / Bug-Report → Structured Ticket Agent — Project 5 from eLearning_SpeakerScript.md

Loads your ticket template, severity rubric, and component/owner map from the
templates/ folder, then converts pasted meeting notes or bug reports into
properly structured tickets.

Usage:
  python ticket_builder.py

Paste your meeting notes or a bug report when prompted, then press Enter twice.
"""

import os
import anthropic
from pathlib import Path

# Load .env if present
_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

SYSTEM_PROMPT = (
    "You are a structured-work agent. "
    "Convert pasted meeting notes or a bug report into tickets that exactly follow the templates provided below. "
    "Each ticket must have: an action-oriented title, context, acceptance criteria, severity (from the rubric), "
    "and the suspected component and owner. "
    "For bug reports also include numbered reproduction steps and flag any assumptions or missing fields. "
    "Ask for missing critical fields rather than guessing. "
    "If the input contains multiple work items, produce one ticket per item."
)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def load_templates() -> str:
    if not TEMPLATES_DIR.exists():
        return ""
    parts = []
    for path in sorted(TEMPLATES_DIR.rglob("*")):
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                parts.append(f"=== {path.relative_to(TEMPLATES_DIR)} ===\n{text}")
            except OSError:
                pass
    return "\n\n".join(parts)


def build_system_prompt() -> str:
    templates = load_templates()
    if not templates:
        print(
            "[Info] templates/ is empty or missing. "
            "Add your ticket template, definition-of-done, severity rubric, and component/owner map there.\n"
        )
        return SYSTEM_PROMPT
    return f"{SYSTEM_PROMPT}\n\n--- TEMPLATES & RULES ---\n{templates}\n--- END TEMPLATES ---"


def read_multiline_input(prompt: str) -> str:
    """Read input until the user submits a blank line on its own."""
    print(prompt)
    lines: list[str] = []
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            print()
            return "quit"
        if line == "" and lines:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _make_client() -> anthropic.Anthropic:
    workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID", "")
    headers = {"anthropic-workspace-id": workspace_id} if workspace_id else {}
    return anthropic.Anthropic(default_headers=headers)


def run() -> None:
    client = _make_client()
    system = build_system_prompt()
    messages: list[dict] = []

    print("Ticket Builder — paste meeting notes or a bug report, then press Enter on a blank line.")
    print("Type 'quit' and Enter to exit.\n")

    while True:
        raw = read_multiline_input("Input:")

        if raw.lower() in ("quit", "exit", "q"):
            break
        if not raw:
            continue

        messages.append({"role": "user", "content": raw})

        print("\n" + "─" * 60)
        with client.messages.stream(
            model="claude-opus-5",
            max_tokens=4096,
            system=system,
            messages=messages,
        ) as stream:
            response_text = ""
            for chunk in stream.text_stream:
                print(chunk, end="", flush=True)
                response_text += chunk

        print("\n" + "─" * 60 + "\n")
        messages.append({"role": "assistant", "content": response_text})


if __name__ == "__main__":
    run()
