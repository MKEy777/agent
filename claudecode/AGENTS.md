# Claudecode (Zero) — Python Claude Code Reimplementation

A pure Python reimplementation of Anthropic's Claude Code CLI. Replicates the CC agent kernel: state machine loop, 22+ built-in tools, MCP, memory, agent teams/swarm, permissions, context compression.

## Tech Stack

- **Runtime**: Python 3.12+ (uv recommended)
- **CLI**: Click
- **API**: Anthropic Python SDK
- **UI**: Rich (terminal rendering)
- **Testing**: pytest (498 tests)

## Entry Points

| File | Purpose |
|------|---------|
| `__main__.py` | `python -m cc` — delegates to `main.py` |
| `main.py` | CLI entry: `main()` Click command, REPL loop (`_run_repl`), print mode (`_run_print_mode`), engine wiring (`_build_engine`) |

## Directory Structure

```
claudecode/
├── core/                         # Agent kernel
│   ├── query_loop.py             # The while(true) state machine — 4 phases per turn
│   ├── query_engine.py           # Dependency container (middleware between main & loop)
│   └── events.py                 # QueryEvent types (TextDelta, ToolUseStart, TurnComplete, etc.)
├── api/                          # Anthropic API layer
│   ├── claude.py                 # SSE stream parser → QueryEvent generator
│   ├── client.py                 # Anthropic SDK wrapper
│   └── token_estimation.py       # Token budget estimation
├── tools/                        # 22+ built-in tools
│   ├── base.py                   # Tool ABC, ToolSchema, ToolRegistry
│   ├── orchestration.py          # Batch partitioning + concurrent/serial dispatch
│   ├── streaming_executor.py     # Mid-stream tool execution
│   ├── agent/agent_tool.py       # Sub-agent spawning
│   ├── bash/bash_tool.py         # Shell execution
│   ├── file_read/file_read_tool.py
│   ├── file_write/file_write_tool.py
│   ├── file_edit/file_edit_tool.py
│   ├── glob_tool/glob_tool.py
│   ├── grep_tool/grep_tool.py
│   ├── web_fetch/web_fetch_tool.py
│   ├── web_search/web_search_tool.py
│   ├── ask_user/ask_user_tool.py
│   ├── todo/todo_write_tool.py
│   ├── skill/skill_tool.py       # Skill loading via tool call
│   ├── mcp_tool/                 # MCP tool bridge
│   ├── task_tools/task_tools.py  # Task create/get/list/stop/update
│   ├── team/                     # Team create/delete
│   └── ... (notebook, plan_mode, send_message, brief, tool_search, lsp)
├── prompts/                      # System prompt assembly
│   ├── builder.py                # build_system_prompt() — 12+ segments
│   ├── claudemd.py               # CLAUDE.md discovery + @include resolution
│   ├── coordinator_prompt.py     # Multi-agent orchestration prompts
│   └── teammate_prompt.py        # Sub-agent behavior prompts
├── permissions/                  # Permission gating
│   ├── gate.py                   # PermissionContext, PermissionMode (bypass/accept_edits/default)
│   └── rules.py                  # Rule engine
├── swarm/                        # Agent teams / multi-agent
│   ├── coordinator.py            # Coordinator orchestration
│   ├── in_process_runner.py      # In-process sub-agent
│   ├── mailbox.py                # Inter-agent message queue
│   └── spawn.py                  # Teammate spawning
├── compact/                      # Context compression
│   └── compact.py                # Summarization-based auto-compact
├── memory/                       # Long-term memory
│   ├── session_memory.py         # Memory file I/O
│   └── extractor.py              # Background memory extraction
├── mcp/                          # Model Context Protocol
│   ├── client.py                 # stdio MCP client
│   └── config.py                 # mcp.json loader
├── session/                      # Session persistence
│   ├── storage.py                # save/load sessions
│   ├── recovery.py               # Orphaned tool_use repair
│   └── task_registry.py          # Background task state tracking
├── skills/                       # Skill system
│   └── loader.py                 # SKILL.md loading from ~/.claude/skills/
├── hooks/                        # Pre/Post tool hook system
├── commands/                     # Slash commands (/help, /clear, /model, etc.)
├── ui/                           # Rich-based terminal renderer
└── models/                       # Data types (Message, ContentBlock, state)
```

## Key Subsystems

- **Query loop** (`core/query_loop.py`): the agent state machine — prepare → model call → error recovery → tool execute, repeat until `end_turn`
- **Tools** (`tools/`): 22+ tool implementations with batch orchestration and streaming execution
- **Swarm** (`swarm/`): multi-agent coordination via `InProcessTeammate` + `Mailbox` communication
- **Prompts** (`prompts/`): 12+ prompt segments assembled dynamically, includes CLAUDE.md discovery

## Quick Start

```bash
uv sync                              # Install dependencies
export ANTHROPIC_API_KEY=sk-...
python -m cc                         # REPL mode
python -m cc -p < task.md           # Print (pipe) mode
```

## Testing

```bash
pytest                               # Run all 498 tests
```
