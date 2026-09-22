"""
AI Agent Launcher — Dev Productivity Suite

Provides a menu to launch either agent described in eLearning_SpeakerScript.md:
  1. Codebase "Why" Oracle  — onboarding + tribal-knowledge Q&A
  2. Ticket Builder          — meeting notes / bug report → structured tickets
"""

import os
import sys
from pathlib import Path


def check_api_key() -> bool:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True

    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY=") and not line.endswith("..."):
                key = line.split("=", 1)[1].strip()
                if key:
                    os.environ["ANTHROPIC_API_KEY"] = key
                    return True

    return False


def print_menu() -> None:
    print("=" * 50)
    print("  Swimple — Dev Productivity Agent Suite")
    print("=" * 50)
    print("  1. Why Oracle (text)")
    print("     Ask why anything is built the way it is")
    print()
    print("  2. Ticket Builder")
    print("     Paste meeting notes or a bug report,")
    print("     get structured tickets back")
    print()
    print("  3. Voice Oracle")
    print("     Speak your questions, hear the answers")
    print()
    print("  q. Quit")
    print("=" * 50)


def main() -> None:
    if not check_api_key():
        print(
            "Error: ANTHROPIC_API_KEY is not set.\n"
            "  Option A: set it in your shell —  export ANTHROPIC_API_KEY=sk-ant-...\n"
            "  Option B: copy .env.example to .env and fill in your key."
        )
        sys.exit(1)

    while True:
        print_menu()
        try:
            choice = input("Choose [1/2/q]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice == "1":
            print()
            import why_oracle
            why_oracle.run()
        elif choice == "2":
            print()
            import ticket_builder
            ticket_builder.run()
        elif choice == "3":
            print()
            import voice_oracle
            voice_oracle.run()
        elif choice in ("q", "quit", "exit"):
            break
        else:
            print("Invalid choice — enter 1, 2, 3, or q.\n")


if __name__ == "__main__":
    main()
