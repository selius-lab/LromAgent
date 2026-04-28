# LromAgent# LLM-ROM Architecture — Persistent Knowledge Retrieval via Multi-Agent Long-Chain Reasoning

**PoC v1.0** — A 3-tier hierarchical multi-agent system that enables LLMs to autonomously investigate, retrieve, and verify information from persistent storage across sessions.

## Architecture

```
User Input
    │
    ▼
┌─────────────────────────────┐
│ Tier 1:  Main Agent         │  Commander / Intent Interpreter
│ (heavy model)               │  Loop: investigate or reply
└───────────┬─────────────────┘
            │ investigation_request
            ▼
┌─────────────────────────────┐
│ Tier 2:  ROM Main Agent     │  Research Planner / Scatter-Gather Hub
│ (heavy model)               │  Loop: dispatch sub-tasks or report
└───────────┬─────────────────┘
            │ dispatch_sub_tasks (parallel)
            ▼
┌─────────────────────────────┐
│ Tier 3:  ROM Sub Agent x N  │  Field Investigator / Tool Executor
│ (light model)               │  Autonomous tool loop (max 5 iterations)
│                             │  Tools: vector_search, absolute_search
└───────────┬─────────────────┘
            │ Search Results (JSON)
            ▼
┌─────────────────────────────┐
│  LocalDatabase              │  Persistent Storage
│  (SQLite + JSON Logs)       │  Past session logs + external knowledge
└─────────────────────────────┘
```

## Directory Structure

```
src/
├── main.py               # CLI entry point
├── agents/
│   ├── main_agent.py     # Tier 1 — user-facing commander agent
│   ├── rom_main_agent.py # Tier 2 — research planner & Scatter-Gather hub
│   └── rom_sub_agent.py  # Tier 3 — autonomous search executor
├── core/
│   ├── orchestrator.py   # Central lifecycle manager (3-tier loop)
│   ├── llm_client.py     # OpenRouter async LLM client
│   └── prompts.py        # System prompt loader
├── db/
│   └── local_database.py # SQLite + JSON log persistence
├── prompts/
│   ├── main_agent_skill.md
│   ├── rom_main_skill.md
│   └── rom_sub_skill.md
└── logs/                  # Session logs (auto-generated, gitignored)
```

## Key Features

- **3-Tier Multi-Agent Collaboration** — Hierarchical commander → planner → executor architecture
- **Long-Chain Reasoning** — Each agent outputs explicit Chain of Thought before structured JSON actions
- **Scatter-Gather (Map-Reduce) Pattern** — Parallel sub-task dispatch via `asyncio.gather()`
- **Recurrent Feedback Loops** — Agents iteratively investigate until confident enough to answer
- **Anti-Hallucination** — Graceful failure reporting when information is not found
- **Persistent Episodic Memory** — All agent interactions logged with hierarchical IDs for cross-session retrieval
- **Tool-Using Sub-Agents** — Autonomous search with vector and chronological queries

## Requirements

- Python 3.11+
- `openai` Python package
- `OPENROUTER_API_KEY` environment variable

## Quick Start

```bash
# Set your API key
export OPENROUTER_API_KEY="sk-or-v1-..."

# Run
python3 src/main.py
```

## Models

| Tier | Model | Role |
|------|-------|------|
| Tier 1 / Tier 2 | Heavy (e.g., z-ai/glm-5.1) | Planning, reasoning, command |
| Tier 3 | Light (e.g., qwen27B) | Fast parallel search execution |

Configured in `core/llm_client.py` — easily swappable via OpenRouter.

## License

MIT
