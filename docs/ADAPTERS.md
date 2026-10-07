# DBNT Adapters - Current and Planned

## Core Adapters (Included)

### `generic`
File-based adapter. Initializes and synchronizes rules under `$DBNT_DIR/rules/`
(default `~/.dbnt/rules/`). It does not run a watcher.

### `claude-code`
Installs score-tracking and transcript-extraction hooks under `~/.claude/hooks/`.
Its existing `sync_rule` target remains `~/.claude/rules/` for compatibility;
score and learning state use `$DBNT_DIR`. 0.6.0 does not inject those files into
context automatically.

## Planned Adapters

### IDE Integrations

| Adapter | Status | Description |
|---------|--------|-------------|
| `cursor` | Planned | Cursor IDE - inject into .cursorrules |
| `vscode` | Planned | VS Code - extension or settings.json |
| `windsurf` | Planned | Windsurf IDE integration |
| `zed` | Planned | Zed editor assistant rules |

### AI Frameworks

| Adapter | Status | Description |
|---------|--------|-------------|
| `langchain` | Planned | LangChain callback handler |
| `langgraph` | Planned | LangGraph state injection |
| `openai` | Planned | OpenAI API wrapper with signal detection |
| `anthropic` | Planned | Anthropic API wrapper |
| `ollama` | Planned | Local Ollama integration |
| `crewai` | Planned | CrewAI agent memory |
| `autogen` | Planned | Microsoft AutoGen integration |

### Agent Frameworks

| Adapter | Status | Description |
|---------|--------|-------------|
| `browser-use` | Planned | Browser Use agent learning |
| `computer-use` | Planned | Anthropic Computer Use integration |
| `mcp` | Planned | Model Context Protocol server |
| `agent-sdk` | Planned | Claude Agent SDK integration |

### Observability

| Adapter | Status | Description |
|---------|--------|-------------|
| `braintrust` | Planned | Braintrust logging + learning extraction |
| `langsmith` | Planned | LangSmith trace analysis |
| `phoenix` | Planned | Arize Phoenix integration |
| `weave` | Planned | Weights & Biases Weave |

### Storage Backends

| Adapter | Status | Description |
|---------|--------|-------------|
| `sqlite` | Planned | SQLite rule storage |
| `postgres` | Planned | PostgreSQL for teams |
| `redis` | Planned | Redis for fast lookups |
| `s3` | Planned | S3 for distributed teams |

## Adapter Interface

All adapters implement `BaseAdapter`:

```python
class BaseAdapter(ABC):
    @abstractmethod
    def install(self) -> None:
        """Install DBNT into the target system."""

    @abstractmethod
    def uninstall(self) -> None:
        """Remove DBNT from the target system."""

    @abstractmethod
    def get_rules_path(self) -> Path:
        """Get the path where rules are stored."""

    @abstractmethod
    def sync_rule(self, rule: Rule) -> None:
        """Sync a rule to the target system's format."""

    @abstractmethod
    def is_installed(self) -> bool:
        """Check if DBNT is installed in the target system."""
```

## Multi-Adapter Coordination

DBNT 0.6.0 does not load a `dbnt.yaml` adapter fan-out configuration or
automatically propagate rules. A host application may instantiate adapters and
call `sync_rule` explicitly. The following is a roadmap sketch, not supported
configuration:

```yaml
# dbnt.yaml
adapters:
  - type: claude-code
    enabled: true
  - type: cursor
    enabled: true
  - type: braintrust
    enabled: true
    config:
      project: my-project
```

Transport, conflict handling, synchronization, and multi-node propagation are
host responsibilities.

## Contributing an Adapter

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the adapter skeleton.

Key considerations:
1. How does the target system consume rules?
2. What format does it expect? (markdown, json, yaml)
3. Can we inject a signal detection hook?
4. How do we sync bidirectionally?
