# Hermes Agent — Self-Improving AI Agent

By Nous Research (MIT). A self-improving AI agent with built-in learning loops, skill creation, cross-platform messaging gateway, cron scheduling, subagent delegation, and terminal/browser control.

## Tech Stack

- **Runtime**: Python 3.12+ (uv), npm workspace (TUI)
- **Testing**: pytest (17K tests, 900 files), vitest (JS)
- **CLI**: argparse, curses UI, Ink (React) TUI
- **PM**: uv for Python, npm workspace for JS

## Entry Points

| File | Purpose |
|------|---------|
| `run_agent.py` | `AIAgent` class — core conversation loop (~12K LOC) |
| `cli.py` | `HermesCLI` class — interactive CLI orchestrator (~11K LOC) |
| `hermes_cli/main.py` | Main CLI entry (argparse dispatch) |
| `model_tools.py` | Tool orchestration — `discover_builtin_tools()`, `handle_function_call()` |
| `toolsets.py` | Toolset definitions, `_HERMES_CORE_TOOLS` list |
| `gateway/run.py` | Messaging gateway runner |
| `tui_gateway/server.py` | TUI JSON-RPC server |
| `acp_adapter/entry.py` | Agent Communication Protocol server |
| `mcp_serve.py` | MCP server entry point |

## Directory Structure

```
hermes-agent/
├── agent/                         # Core agent (124+ files)
│   ├── conversation_loop.py       # Main agent loop
│   ├── prompt_builder.py          # System prompt assembly
│   ├── memory_manager.py          # Memory orchestration
│   ├── curator.py                 # Skill lifecycle management
│   ├── context_compressor.py      # Context compression
│   ├── tool_executor.py           # Tool execution dispatch
│   ├── provider adapters          # anthropic, gemini, bedrock, vertex, codex adapters
│   ├── moa_loop.py                # Mixture of Agents
│   └── subdirectories: lsp/, pet/, secret_sources/, transports/
├── hermes_cli/                    # CLI subsystem (154+ files)
│   ├── main.py                    # Argparse dispatch
│   ├── config.py                  # Config loading
│   ├── commands.py                # COMMAND_REGISTRY
│   ├── plugins.py                 # PluginManager
│   ├── gateway.py                 # Gateway subcommand
│   ├── cron.py                    # Cron subcommand
│   ├── curse_ui.py                # Curses interactive UI
│   └── subcommands/               # Additional subcommands
├── tools/                         # Tool implementations (102+ files)
│   ├── registry.py                # Tool registry & dispatch
│   ├── terminal_tool.py           # Shell execution
│   ├── file_tools.py              # File I/O
│   ├── web_tools.py               # Web browsing/search
│   ├── browser_*.py               # Browser automation
│   ├── delegate_tool.py           # Subagent delegation
│   ├── memory_tool.py             # Memory interaction
│   ├── todo_tool.py               # Task management
│   ├── mcp_tool.py                # MCP integration
│   └── computer_use/              # Computer use backends
├── gateway/                       # Messaging gateway (48+ files)
│   ├── run.py                     # Gateway runner
│   ├── session.py                 # Session management
│   ├── platforms/                 # 30+ platform adapters
│   │   ├── telegram/ discord/ slack/ whatsapp/ signal/ matrix/
│   │   ├── mattermost/ email/ sms/ irc/ line/ dingtalk/
│   │   ├── wecom/ weixin/ feishu/ qqbot/ teams/
│   │   └── ... (30+ total)
│   └── builtin_hooks/             # Extension hooks
├── plugins/                       # Plugin system
│   ├── model-providers/           # Inference backends
│   ├── memory/                    # Memory providers
│   └── ...
├── skills/                        # Built-in skills (14 categories)
├── optional-skills/               # Heavier/niche skills (20+ categories)
├── cron/                          # Scheduler
├── ui-tui/                        # Ink (React) terminal UI (TS)
├── tui_gateway/                   # Python JSON-RPC for TUI
├── apps/desktop/                  # Electron desktop app
└── tests/                         # pytest suite (17K tests)
```

## Key Subsystems

- **Agent loop** (`agent/conversation_loop.py`): the core state machine driving the agent
- **Tools** (`tools/`): 100+ tool implementations with registry-based discovery
- **Gateway** (`gateway/platforms/`): 30+ messaging platform adapters with unified session management
- **Skills** (`skills/` + `optional-skills/`): skill creation, curation, provenance tracking
- **Memory** (`agent/memory_manager.py`): multi-backend memory with FTS5 search

## Testing

```bash
pytest                           # Run Python test suite
pytest tests/agent/              # Agent tests
pytest tests/tools/              # Tool tests
pytest tests/gateway/            # Gateway tests
```
