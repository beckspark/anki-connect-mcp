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

## Usage with Claude Code

### Add to Claude Code

```bash
# Option 1: Use the sync script (recommended)
python3 ~/.claude/scripts/sync-mcp-server.py

# Option 2: Manually merge .mcp.json into ~/.claude.json
# (Be careful not to overwrite existing servers)
```

### Restart Claude Code

After adding the server, restart Claude Code to load it.

### Example Usage

Once configured, you can ask Claude:

> "Create a flashcard: What is the capital of France? / Paris"

> "Create a cloze card: The {{c1::mitochondria}} is the {{c2::powerhouse}} of the cell in my Biology deck"

> "Make a type-in card for the chemical symbol of gold (Au)"

## MCP Tools

### `create_basic_card`

Create a traditional front/back flashcard.

**Parameters:**
- `front` (required): Question or prompt
- `back` (required): Answer
- `deck` (optional): Deck name (default: "Default")
- `tags` (optional): List of tags
- `validate` (optional): Run quality validation (default: true)

**Example:**
```python
create_basic_card(
    front="What is the capital of France?",
    back="Paris",
    deck="Geography::Europe",
    tags=["capitals", "europe"]
)
```

### `create_cloze_card`

Create a cloze deletion (fill-in-the-blank) flashcard.

**Parameters:**
- `text` (required): Text with {{c1::deletions}}
- `deck` (optional): Deck name
- `tags` (optional): List of tags
- `extra` (optional): Additional context
- `validate` (optional): Run quality validation (default: true)

**Example:**
```python
create_cloze_card(
    text="The {{c1::mitochondria}} is the {{c2::powerhouse}} of the cell.",
    deck="Biology::Cells",
    tags=["cellular_biology"]
)
```

### `create_type_in_card`

Create a flashcard requiring exact typing of the answer.

**Parameters:**
- `front` (required): Question or prompt
- `back` (required): Expected typed answer
- `deck` (optional): Deck name
- `tags` (optional): List of tags
- `validate` (optional): Run quality validation (default: true)

**Example:**
```python
create_type_in_card(
    front="Chemical symbol for gold",
    back="Au",
    deck="Chemistry::Elements"
)
```

### `list_decks`

List all available Anki decks.

**Returns:**
- List of all deck names in your Anki collection

**Example:**
```python
list_decks()
# Returns: Available decks (5 total):
# - Default
# - Biology
# - Biology::Cells
# - Chemistry
# - History::Ancient Rome
```

### `create_deck`

Create a new Anki deck.

**Parameters:**
- `name` (required): Deck name. Use :: for hierarchy (e.g., "Biology::Cells")

**Returns:**
- Success message with deck ID

**Example:**
```python
create_deck("Biology::Molecular Biology")
# Returns: Deck created successfully: Biology::Molecular Biology (ID: 1234567890)
# Hierarchy: Biology → Molecular Biology
```

### `get_deck_stats`

Get statistics for an Anki deck.

**Parameters:**
- `deck_name` (required): Name of the deck

**Returns:**
- Deck statistics (new cards, learning, review counts, total cards)

**Example:**
```python
get_deck_stats("Biology::Cells")
# Returns:
# Statistics for deck: Biology::Cells
#
# New cards: 42
# Learning: 15
# Review: 128
# Total cards: 185
#
# Today's workload: 185 cards
```

## MCP Resources

Resources provide read-only access to data without making tool calls. Claude can query these directly.

### `card-history://recent`

View the 50 most recently created flashcards with their source, deck, and creation time.

**Example:**
```
Recent Card Creation History (50 most recent)
================================================================================

[BASIC] What is the capital of France?
  Deck: Geography::Europe | Source: manual | Created: 2026-01-04 08:45:00
  Anki Note ID: 1234567890

[CLOZE] The {{c1::mitochondria}} is the {{c2::powerhouse}} of...
  Deck: Biology::Cells | Source: pdf | Created: 2026-01-04 08:50:00
  Anki Note ID: 1234567891
```

### `card-history://source/{source_path}`

View all cards generated from a specific PDF, ePub, or other source.

**Example:**
```
Cards Generated from: /home/user/biology.pdf
================================================================================
Total cards: 15

1. [CLOZE] The {{c1::mitochondria}} is the powerhouse of the cell.
   Deck: Biology::Cells | Created: 2026-01-04 08:50:00

2. [BASIC] What is photosynthesis?
   Answer: The process by which plants convert light energy...
   Deck: Biology | Created: 2026-01-04 08:51:00
```

### `card-history://stats`

View aggregated validation statistics across all generated cards.

**Example:**
```
Flashcard Quality Statistics
================================================================================

Total cards created: 150
Cards with validation warnings: 12 (8%)
Cards with no warnings: 138 (92%)

Quality Score: Excellent ✓

Recommendations:
- Review cards with warnings for quality improvements
- Follow minimum information principle (one concept per card)
- Keep answers concise (<50 words)
- Use cloze deletions for factual learning
```

### `card-history://generation-history`

View all generation sessions showing which sources were used to create cards.

**Example:**
```
Card Generation History (100 most recent sessions)
================================================================================

Session #5 [PDF]
  Source: /home/user/chemistry.pdf
  Cards created: 25
  Date: 2026-01-04 09:00:00

Session #4 [MANUAL]
  Source: N/A
  Cards created: 3
  Date: 2026-01-04 08:45:00
```

## HTML Formatting

All card fields support **full HTML formatting**. You can use HTML directly or use the convenient helper functions from the `formatting` module.

### Direct HTML Usage

```python
# Chemical formulas with subscripts
create_basic_card(
    front="What is the formula for water?",
    back="H<sub>2</sub>O",
    deck="Chemistry"
)

# Lists
create_basic_card(
    front="What are the states of matter?",
    back="<ul><li>Solid</li><li>Liquid</li><li>Gas</li></ul>",
    deck="Physics"
)

# Colors and styling
create_basic_card(
    front="What color is a stop sign?",
    back='<span style="color: red; font-weight: bold;">Red</span>',
    deck="Driving"
)

# Cloze cards with HTML
create_cloze_card(
    text="Water has the formula {{c1::H<sub>2</sub>O}}.",
    deck="Chemistry"
)
```

### Using Helper Functions

```python
from anki_connect_mcp.formatting import (
    bold, italic, color, subscript, superscript,
    unordered_list, ordered_list, code
)

# Text formatting
create_basic_card(
    front="What is photosynthesis?",
    back=f"{bold('Definition:')} The process by which plants convert light energy",
    deck="Biology"
)

# Chemical notation
create_basic_card(
    front="What is the formula for sulfuric acid?",
    back=f"H{subscript('2')}SO{subscript('4')}",
    deck="Chemistry"
)

# Math notation
create_basic_card(
    front="What is the Pythagorean theorem?",
    back=f"a{superscript('2')} + b{superscript('2')} = c{superscript('2')}",
    deck="Math"
)

# Lists
steps = unordered_list(["Step 1", "Step 2", "Step 3"])
create_basic_card(
    front="What are the steps?",
    back=steps,
    deck="Procedures"
)
```

### Available Helper Functions

- **Text styling:** `bold()`, `italic()`, `underline()`, `color()`, `highlight()`
- **Scientific notation:** `subscript()`, `superscript()`
- **Lists:** `unordered_list()`, `ordered_list()`
- **Code:** `code()` (inline and block)
- **Tables:** `table()`
- **Math:** `mathjax_inline()`, `mathjax_block()` (LaTeX support)
- **Layout:** `line_break()`, `div()`
- **Utilities:** `strip_html()`, `get_text_length()`

### HTML-Aware Validation

The validation system automatically strips HTML when counting characters and words, so markup doesn't affect length limits:

```python
# This passes validation (counts as 5 chars, not including <b></b>)
create_basic_card(
    front="<b>Short</b>",
    back="Answer",
    deck="Test"
)
```

### Complete Guide

For detailed examples and best practices, see [docs/HTML_FORMATTING.md](docs/HTML_FORMATTING.md).

## Configuration

Environment variables (set in `.env`):

```bash
# AnkiConnect API
ANKI_CONNECT_URL=http://localhost:8765
ANKI_CONNECT_VERSION=6

# Default Behavior
DEFAULT_DECK=Default
GENERATION_MODE=hybrid  # Options: auto, hybrid
VALIDATION_STRICTNESS=moderate  # Options: strict, moderate, lenient

# Validation Thresholds
MAX_ANSWER_WORDS=50

# Content Extraction (for future PDF/ePub support)
EXTRACTION_TIMEOUT=60

# Database
DATABASE_PATH=~/.anki_mcp.db
```

## Validation Rules

The server enforces spaced repetition best practices:

1. **Cloze Format** (ERROR): Ensures valid {{c1::text}} format
2. **Answer Length** (WARNING): Flags answers >50 words (configurable)
3. **Minimum Information** (WARNING): Detects multi-concept cards
4. **Ambiguity** (SUGGESTION): Flags vague questions
5. **Cloze Count** (WARNING): Warns if >3 deletions per card
6. **Context** (SUGGESTION): Ensures standalone comprehension

### Validation Severity Levels

- **ERROR**: Blocks card creation
- **WARNING**: Shows warning but allows creation
- **SUGGESTION**: Best practice tip

## Troubleshooting

### "Failed to connect to Anki"

1. Ensure Anki is running
2. Verify AnkiConnect is installed (Tools → Add-ons)
3. Check ANKI_CONNECT_URL in `.env` (default: http://localhost:8765)

### "Card validation failed"

The server enforces quality standards. Common issues:

- **Cloze format**: Use `{{c1::text}}` not `{c1:text}`
- **Long answers**: Split multi-concept cards into separate cards
- **Multiple questions**: One concept per card (minimum information principle)

Set `validate=false` to bypass validation (not recommended).

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
- ⏳ PDF text extraction
- ⏳ ePub text extraction
- ⏳ Batch card creation (hybrid mode preview)
- ⏳ Web content extraction

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
