# AI Agent Projects — Dev Productivity

## Project 1 — The Codebase "Why" Oracle (onboarding + tribal-knowledge agent)

**Problem it solves.** Onboarding to unfamiliar code and re-deriving "why is it built this way?" is one of the biggest silent time sinks. Gathering project context and waiting on approvals are two of the biggest productivity leaks (~26% each), and per the 2024 Stack Overflow Developer Survey (~65,000 respondents), 61% of developers spend more than 30 minutes a day searching for answers — roughly a full workday per week. Where the right context exists, ramp accelerates sharply: DX's Q4 2025 AI-assisted engineering Impact Report (six multinational enterprises) found engineers using AI daily hit their 10th PR in 49 days — nearly half the 91 days it took peers without AI.

**Why it's a good fit for AI — and specifically agentic/instruction-based.** A one-off prompt can't remember your architecture; a project with a curated knowledge base answers grounded, repeatable questions ("where does auth happen?", "why Postgres over Mongo?", "what's the retry policy and why?") without a senior engineer acting as a human router. As one practitioner guide put it, the bottleneck was never reading speed — it was senior-engineer translation capacity, which this offloads.

**Time saved weekly.** For a developer new to a codebase or working across many services: ~2–4 hours/week of self-directed spelunking and interrupting teammates, plus much larger one-time savings during onboarding.

**How to build it (beginner).** Create a Claude Project (or custom GPT). Knowledge base: your README(s), architecture docs, any ADRs (architecture decision records), a directory map, key config files, and — powerfully — an export of merged-PR descriptions and design docs that capture the "why." Instructions: *"You are a codebase onboarding engineer. Answer only from the uploaded material and cite the file. Trace code paths step by step. If the answer isn't in the knowledge base, say so — never invent conventions."* Intermediate upgrade: maintain a living `CLAUDE.md` in the repo and run it through Claude Code so it reads the actual source on demand; teams report a good context file cuts repetitive explanations by 80%+.

---

## Project 5 — The Meeting/Bug-Report-to-Structured-Work Agent

**Problem it solves.** The gap between conversation and execution: after every standup, planning, or bug-report thread, someone reconstructs action items into properly formatted tickets. Per Atlassian's 2025 report, 50% of developers lose 10+ hours/week to organizational inefficiencies including unclear requirements and communication overhead, and roughly 23% of developer time goes to meetings and operational tasks.

**Why AI / agentic.** Turning rambling transcripts or vague bug reports into consistent, well-structured tickets (title, context, acceptance criteria, repro steps, severity) is a formatting+extraction task with a fixed schema — a perfect standing instruction, not a re-typed prompt. Two flavors: (a) meeting notes → tickets, and (b) raw bug report → triage summary + reproduction steps + a failing test. On the bug side, "cannot reproduce" is the single most expensive phrase in support, and developers spend up to 45% of bug-fixing time clarifying incomplete reports.

**Time saved weekly.** ~1–3 hours/week of post-meeting admin and back-and-forth on under-specified tickets; one SaaS team reported cutting post-meeting admin by 73%.

**How to build it (beginner).** Custom GPT or Claude Project. Knowledge base: your ticket template, definition-of-done, severity rubric, and component/owner map. Instruction: *"Convert pasted notes or a bug report into tickets in our exact template. Each ticket: action-oriented title, context, acceptance criteria, severity, suspected component/owner. For bug reports, also produce numbered reproduction steps and flag your assumptions. Ask for missing critical fields rather than guessing."* Intermediate: a custom GPT with an Action that posts directly to Jira/Linear/GitHub Issues, or an n8n/UiPath flow that ingests a transcript and creates tickets automatically (production examples of both exist).

---

## How to Set These Up as a Project in Claude

Claude Projects give you a persistent workspace with standing instructions and a knowledge base, so you're not re-explaining context every chat. Here's how to build each one:

1. **Create the Project.** In the Claude sidebar, click **Projects → New project**. Give it a clear name (e.g. "Codebase Why-Oracle" or "Ticket Builder").

2. **Set the custom instructions.** Open **Project settings → Custom instructions** (sometimes shown as "Set custom instructions" on the project page). Paste in the instruction block from above — this becomes the standing system prompt for every conversation inside the project, so you never retype it.

3. **Upload the knowledge base.** Use **Add content** on the project page to upload files:
   - *Why Oracle:* README(s), architecture docs, ADRs, a directory map, key config files, exported merged-PR descriptions/design docs.
   - *Ticket Builder:* your ticket template, definition-of-done doc, severity rubric, component/owner map.
   
   Claude reads everything in the project's knowledge base automatically in every chat you start there — no need to re-paste it.

4. **Start a chat inside the project.** From the project page, click **New chat**. Any conversation started here inherits the instructions + knowledge base. Paste in a diff/log/question (Why Oracle) or meeting notes/bug report (Ticket Builder) and it'll respond per the rules you set.

5. **Iterate the instructions, don't restart the chat.** When it gets something wrong in a way that'll recur, go back into **Custom instructions** and add a line, or drop a new doc into the knowledge base. Over time the corrections compound and the agent gets reliably better — that's what turns this from "a chat" into "an agent."

6. **Keep a human gate.** For now, treat outputs as drafts to review — copy the generated ticket into Jira/Linear yourself, or paste the "why" answer into your PR/wiki after a quick sanity check. Once you trust it, you can look at automating the posting step (e.g. Claude Code, a small script, or a Zapier/n8n flow).
