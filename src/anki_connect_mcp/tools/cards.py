"""MCP tools for creating and managing Anki flashcards."""

from mcp.types import CallToolResult, TextContent

from ..client import AnkiConnectionError, get_anki_client
from ..config import settings
from ..db import get_database
from ..models import BasicCard, ClozeCard, TypeInCard
from ..server import app
from ..validators import get_validator


@app.tool()
async def create_basic_card(
    front: str,
    back: str,
    deck: str | None = None,
    tags: list[str] | None = None,
    validate: bool = True,
) -> CallToolResult:
    """Create a basic flashcard with front and back sides.

    Creates a traditional flashcard with a question/prompt on the front and answer on the back.
    Automatically validates against spaced repetition best practices unless disabled.

    Args:
        front: Question or prompt text (max 1000 chars)
        back: Answer text (max 2000 chars)
        deck: Deck name (uses default if not specified). Supports hierarchy with ::
              (e.g., "Biology::Cells")
        tags: List of tags to apply to the card
        validate: Whether to run quality validation (default: True)

    Returns:
        Success message with note ID and any validation warnings, or error message

    Example:
        >>> create_basic_card(
        ...     front="What is the capital of France?",
        ...     back="Paris",
        ...     deck="Geography::Europe",
        ...     tags=["capitals", "europe"]
        ... )
    """
    try:
        # Create and validate card
        card = BasicCard(
            front=front, back=back, deck=deck or settings.default_deck, tags=tags or []
        )

        warnings = []
        suggestions = []

        if validate:
            validator = get_validator()
            errors = validator.get_errors(card)

            # Block on errors
            if errors:
                error_msgs = "\n".join(f"- {e.message}" for e in errors)
                return CallToolResult(
                    isError=True,
                    content=[
                        TextContent(
                            type="text",
                            text=f"Card validation failed:\n{error_msgs}\n\n"
                            f"Please fix these issues and try again.",
                        )
                    ],
                )

            warnings = validator.get_warnings(card)
            suggestions = validator.get_suggestions(card)

        # Create note in Anki
        client = get_anki_client()
        note = {
            "deckName": card.deck,
            "modelName": "Basic",
            "fields": {"Front": card.front, "Back": card.back},
            "tags": card.tags,
        }

        note_id = await client.add_note(note)

        # Log to database
        db = get_database()
        generation_id = db.create_generation(source_type="manual")
        db.add_generated_card(
            generation_id=generation_id,
            anki_note_id=note_id,
            card_type="basic",
            front_or_text=card.front,
            back=card.back,
            deck=deck or settings.default_deck,
            tags=card.tags,
            validation_warnings=[w.model_dump() for w in warnings] if warnings else None,
        )

        # Build response message
        msg = f"Card created successfully (Anki note ID: {note_id})\n\nDeck: {card.deck}"

        if warnings:
            msg += "\n\nWarnings:\n" + "\n".join(f"- {w.message}" for w in warnings)

        if suggestions:
            msg += "\n\nSuggestions:\n" + "\n".join(f"- {s.message}" for s in suggestions)

        return CallToolResult(content=[TextContent(type="text", text=msg)])

    except AnkiConnectionError as e:
        return CallToolResult(
            isError=True,
            content=[
                TextContent(
                    type="text",
                    text=(
                        "Failed to connect to Anki. "
                        "Is Anki running with AnkiConnect installed?\n\n"
                        f"Error: {str(e)}"
                    ),
                )
            ],
        )
    except Exception as e:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Unexpected error: {str(e)}")],
        )


@app.tool()
async def create_cloze_card(
    text: str,
    deck: str | None = None,
    tags: list[str] | None = None,
    extra: str | None = None,
    validate: bool = True,
) -> CallToolResult:
    """Create a cloze deletion flashcard.

    Cloze deletions are fill-in-the-blank style cards. Research shows they're more effective
    for factual learning than basic cards. Use {{c1::text}} format for deletions.

    Args:
        text: Text with cloze deletions. Format: {{c1::answer}} or {{c1::answer::hint}}
              Use c1, c2, c3, etc. for multiple deletions
        deck: Deck name (uses default if not specified)
        tags: List of tags to apply to the card
        extra: Additional context or hints shown on all cards
        validate: Whether to run quality validation (default: True)

    Returns:
        Success message with note ID and any validation warnings, or error message

    Example:
        >>> create_cloze_card(
        ...     text="The {{c1::mitochondria}} is the {{c2::powerhouse}} of the cell.",
        ...     deck="Biology::Cells",
        ...     tags=["cellular_biology", "organelles"]
        ... )
    """
    try:
        # Create and validate card
        card = ClozeCard(
            text=text,
            deck=deck or settings.default_deck,
            tags=tags or [],
            extra=extra,
        )

        warnings = []
        suggestions = []

        if validate:
            validator = get_validator()
            errors = validator.get_errors(card)

            # Block on errors
            if errors:
                error_msgs = "\n".join(f"- {e.message}" for e in errors)
                return CallToolResult(
                    isError=True,
                    content=[
                        TextContent(
                            type="text",
                            text=f"Card validation failed:\n{error_msgs}\n\n"
                            f"Please fix these issues and try again.",
                        )
                    ],
                )

            warnings = validator.get_warnings(card)
            suggestions = validator.get_suggestions(card)

        # Create note in Anki
        client = get_anki_client()
        fields = {"Text": card.text}
        if card.extra:
            fields["Extra"] = card.extra

        note = {
            "deckName": card.deck,
            "modelName": "Cloze",
            "fields": fields,
            "tags": card.tags,
        }

        note_id = await client.add_note(note)

        # Log to database
        db = get_database()
        generation_id = db.create_generation(source_type="manual")
        db.add_generated_card(
            generation_id=generation_id,
            anki_note_id=note_id,
            card_type="cloze",
            front_or_text=card.text,
            back=None,
            deck=deck or settings.default_deck,
            tags=card.tags,
            validation_warnings=[w.model_dump() for w in warnings] if warnings else None,
        )

        # Build response message
        msg = f"Cloze card created successfully (Anki note ID: {note_id})\n\nDeck: {card.deck}"

        if warnings:
            msg += "\n\nWarnings:\n" + "\n".join(f"- {w.message}" for w in warnings)

        if suggestions:
            msg += "\n\nSuggestions:\n" + "\n".join(f"- {s.message}" for s in suggestions)

        return CallToolResult(content=[TextContent(type="text", text=msg)])

    except AnkiConnectionError as e:
        return CallToolResult(
            isError=True,
            content=[
                TextContent(
                    type="text",
                    text=(
                        "Failed to connect to Anki. "
                        "Is Anki running with AnkiConnect installed?\n\n"
                        f"Error: {str(e)}"
                    ),
                )
            ],
        )
    except Exception as e:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Unexpected error: {str(e)}")],
        )


@app.tool()
async def create_type_in_card(
    front: str,
    back: str,
    deck: str | None = None,
    tags: list[str] | None = None,
    validate: bool = True,
) -> CallToolResult:
    """Create a type-in answer flashcard.

    Type-in cards require typing the exact answer, testing recall more rigorously than
    basic cards. Best for learning precise terms, spellings, or short definitions.

    Args:
        front: Question or prompt text
        back: Expected typed answer (must match exactly)
        deck: Deck name (uses default if not specified)
        tags: List of tags to apply to the card
        validate: Whether to run quality validation (default: True)

    Returns:
        Success message with note ID and any validation warnings, or error message

    Example:
        >>> create_type_in_card(
        ...     front="Chemical symbol for gold",
        ...     back="Au",
        ...     deck="Chemistry::Elements"
        ... )
    """
    try:
        # Create and validate card
        card = TypeInCard(
            front=front, back=back, deck=deck or settings.default_deck, tags=tags or []
        )

        warnings = []
        suggestions = []

        if validate:
            validator = get_validator()
            errors = validator.get_errors(card)

            # Block on errors
            if errors:
                error_msgs = "\n".join(f"- {e.message}" for e in errors)
                return CallToolResult(
                    isError=True,
                    content=[
                        TextContent(
                            type="text",
                            text=f"Card validation failed:\n{error_msgs}\n\n"
                            f"Please fix these issues and try again.",
                        )
                    ],
                )

            warnings = validator.get_warnings(card)
            suggestions = validator.get_suggestions(card)

        # Create note in Anki
        client = get_anki_client()
        note = {
            "deckName": card.deck,
            "modelName": "Basic (type in the answer)",
            "fields": {"Front": card.front, "Back": card.back},
            "tags": card.tags,
        }

        note_id = await client.add_note(note)

        # Log to database
        db = get_database()
        generation_id = db.create_generation(source_type="manual")
        db.add_generated_card(
            generation_id=generation_id,
            anki_note_id=note_id,
            card_type="type_in",
            front_or_text=card.front,
            back=card.back,
            deck=deck or settings.default_deck,
            tags=card.tags,
            validation_warnings=[w.model_dump() for w in warnings] if warnings else None,
        )

        # Build response message
        msg = f"Type-in card created successfully (Anki note ID: {note_id})\n\nDeck: {card.deck}"

        if warnings:
            msg += "\n\nWarnings:\n" + "\n".join(f"- {w.message}" for w in warnings)

        if suggestions:
            msg += "\n\nSuggestions:\n" + "\n".join(f"- {s.message}" for s in suggestions)

        return CallToolResult(content=[TextContent(type="text", text=msg)])

    except AnkiConnectionError as e:
        return CallToolResult(
            isError=True,
            content=[
                TextContent(
                    type="text",
                    text=(
                        "Failed to connect to Anki. "
                        "Is Anki running with AnkiConnect installed?\n\n"
                        f"Error: {str(e)}"
                    ),
                )
            ],
        )
    except Exception as e:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Unexpected error: {str(e)}")],
        )
