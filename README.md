# Swimple — Dev Productivity AI Agent Suite

> Ask your codebase *why*. Convert chaos into tickets. Use your voice.

Swimple is a suite of three AI agents built on the Claude API and a Neo4j knowledge graph. It turns tribal engineering knowledge into instant answers, converts messy meeting notes into structured tickets, and lets you speak your questions out loud.

---

## Agents

### ◆ Why Oracle
Ask *why* anything in the codebase is built the way it is. The Oracle queries a Neo4j knowledge graph populated from your architecture docs, ADRs, and design decisions — then answers with grounded citations, not hallucinations.

### ◈ Ticket Builder
Paste standup notes, a bug report, or a feature request. Get back properly structured tickets — one per work item — with severity, acceptance criteria, component owner, and flagged assumptions.

### 🎙 Voice Oracle
The same Why Oracle, hands-free. Speak your question, hear the answer. Uses browser Web Speech API (Chrome/Edge) for input and your OS voice for playback.

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| AI | Claude Opus 5 (Anthropic) | Streaming, grounded responses |
| Knowledge graph | Neo4j AuraDB | Relationship-first codebase queries |
| Voice STT | Web Speech API / SpeechRecognition | Zero API cost |
| Voice TTS | Web Speech Synthesis / pyttsx3 | Offline, no API key |
| UI | Vanilla HTML/CSS/JS | Zero build step, ships anywhere |

---

## Project Structure

```
swimpleAi/
├── main.py                  # Agent launcher menu
├── why_oracle.py            # Text-mode Why Oracle
├── ticket_builder.py        # Ticket Builder agent
├── voice_oracle.py          # Voice-enabled Oracle
├── graph/
│   ├── ingest.py            # Claude extracts entities → Neo4j
│   └── query.py             # Cypher context retrieval
├── knowledge_base/          # Drop your docs here (markdown, txt)
├── templates/               # Ticket template + severity rubric
├── docker-compose.yml       # Local Neo4j 5.24
├── requirements.txt
└── .env.example             # Credential template
```

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/Thobane-Sithole/swimpleAi.git
cd swimpleAi
pip install -r requirements.txt
```

### 2. Set up credentials

```bash
cp .env.example .env
# Edit .env and fill in:
#   ANTHROPIC_API_KEY    — console.anthropic.com
#   ANTHROPIC_WORKSPACE_ID (if using a workspace key)
#   NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD
#   NEO4J_DATABASE       — AuraDB instance name
```

### 3. Start Neo4j (choose one)

**Local Docker:**
```bash
docker-compose up -d
```

**Cloud:** Use [Neo4j AuraDB](https://console.neo4j.io) free tier — copy the connection details into `.env`.

### 4. Ingest your knowledge base

Drop your architecture docs, ADRs, and design decision records into `knowledge_base/`, then:

```bash
python -m graph.ingest
```

Claude reads every file, extracts components / technologies / decisions as a graph, and loads them into Neo4j.

### 5. Run

```bash
python main.py
```

Pick an agent from the menu:

```
  1. Why Oracle (text)
  2. Ticket Builder
  3. Voice Oracle
```

---

## Web UI

The Swimple web interface (dark theme, agent switcher, voice mic button, auto-speak responses) runs as a standalone HTML file — no server required.

Open `swimple_ui.html` in Chrome or Edge, or deploy it to any static host.

---

## Knowledge Graph Schema

```
(Document)-[:DESCRIBES]->(Component)
(Document)-[:RECORDS]->(Decision)
(Document)-[:MENTIONS]->(Technology)
(Decision)-[:CHOOSES]->(Technology)
(Decision)-[:REJECTS]->(Technology)
(Decision)-[:EXPLAINS]->(Component)
(Component)-[:DEPENDS_ON]->(Component)
(Component)-[:USES]->(Technology)
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `ANTHROPIC_WORKSPACE_ID` | Workspace ID (org keys only) |
| `NEO4J_URI` | Bolt or `neo4j+s://` URI |
| `NEO4J_USERNAME` | Database username |
| `NEO4J_PASSWORD` | Database password |
| `NEO4J_DATABASE` | Database name (AuraDB) |

---

## License

MIT
