# Anki Connect MCP

FastMCP server for creating and managing Anki flashcards via AnkiConnect, with built-in quality validation based on spaced repetition research.

## Features

- **Smart Card Creation**: Create basic, cloze, and type-in flashcards
- **Quality Validation**: Enforces best practices (minimum information principle, optimal answer length, etc.)
- **History Tracking**: DuckDB database tracks which sources generated which cards
- **Multiple Card Types**:
  - Basic (front/back)
  - Cloze deletions (fill-in-the-blank)
  - Type-in answer (exact typing required)
- **Validation Modes**: Strict, moderate, or lenient quality enforcement
- **Generation Modes**: Automatic or hybrid (preview before creating)

## Prerequisites

1. **Anki** must be running
2. **AnkiConnect** plugin must be installed in Anki
   - Install from Anki: Tools → Add-ons → Get Add-ons → Code: `2055492159`
   - Or install Anki-Connect-Plus: https://github.com/Soki-Team/Anki-Connect-Plus

## Installation

```bash
# Clone or navigate to this directory
cd /home/sbeck/code/mcps/anki-connect-mcp

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env

# Edit .env if needed (optional - defaults work for standard setup)
```

## Development Status

**Implemented:**
- ✅ Basic card creation (basic, cloze, type-in)
- ✅ Quality validation (6 rules)
- ✅ HTML formatting support (direct and helper functions)
- ✅ HTML-aware validation (strips tags when counting length)
- ✅ History tracking (DuckDB)
- ✅ Singleton patterns (AnkiConnect client, database)
- ✅ CallToolResult error handling (2026 best practices)
- ✅ Deck management tools (`list_decks`, `create_deck`, `get_deck_stats`)
- ✅ MCP resources for history queries (read-only data access)

**Planned:**
- ⏳ PDF/epub/web text extraction
- Reflection/reflexion multi-"agent" graph process for analyzing and iterating on cards and decks.

## Development

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run basedpyright

# Install pre-commit hooks
uv run pre-commit install
```

## Acknowledgments

Built with:
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework
- [AnkiConnect](https://git.sr.ht/~foosoft/anki-connect) - Anki API
- Research on spaced repetition best practices (SuperMemo, FSRS algorithm)
