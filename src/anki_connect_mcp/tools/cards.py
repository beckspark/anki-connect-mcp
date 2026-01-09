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

    **HTML Formatting:** Both front and back fields support full HTML formatting. You can use:
    - Basic formatting: `<b>bold</b>`, `<i>italic</i>`, `<u>underline</u>`
    - Colors: `<span style="color: red;">text</span>`
    - Lists: `<ul><li>item</li></ul>` or `<ol><li>item</li></ol>`
    - Line breaks: `<br>`
    - Any other standard HTML tags

    For convenience, use the formatting module helpers or pass HTML directly as strings.

    Args:
        front: Question or prompt text (max 1000 chars visible text, HTML tags not counted)
        back: Answer text (max 2000 chars visible text, HTML tags not counted)
        deck: Deck name (uses default if not specified). Supports hierarchy with ::
              (e.g., "Biology::Cells")
        tags: List of tags to apply to the card
        validate: Whether to run quality validation (default: True)

    Returns:
        Success message with note ID and any validation warnings, or error message

    Examples:
        Basic usage:
        >>> create_basic_card(
        ...     front="What is the capital of France?",
        ...     back="Paris",
        ...     deck="Geography::Europe",
        ...     tags=["capitals", "europe"]
        ... )

        With HTML formatting:
        >>> create_basic_card(
        ...     front="What is the chemical formula for <b>water</b>?",
        ...     back="H<sub>2</sub>O",
        ...     deck="Chemistry::Basics"
        ... )

        With complex formatting:
        >>> create_basic_card(
        ...     front="What are the three states of matter?",
        ...     back="<ul><li>Solid</li><li>Liquid</li><li>Gas</li></ul>",
        ...     deck="Physics::Fundamentals"
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

    **HTML Formatting:** Cloze cards support full HTML formatting both inside and outside
    cloze deletions. You can combine cloze syntax with HTML tags seamlessly.

    Args:
        text: Text with cloze deletions. Format: {{c1::answer}} or {{c1::answer::hint}}
              Use c1, c2, c3, etc. for multiple deletions. HTML tags are supported.
        deck: Deck name (uses default if not specified)
        tags: List of tags to apply to the card
        extra: Additional context or hints shown on all cards (supports HTML)
        validate: Whether to run quality validation (default: True)

    Returns:
        Success message with note ID and any validation warnings, or error message

    Examples:
        Basic cloze:
        >>> create_cloze_card(
        ...     text="The {{c1::mitochondria}} is the {{c2::powerhouse}} of the cell.",
        ...     deck="Biology::Cells",
        ...     tags=["cellular_biology", "organelles"]
        ... )

        With HTML formatting:
        >>> create_cloze_card(
        ...     text="Water has the formula {{c1::H<sub>2</sub>O}}.",
        ...     deck="Chemistry::Molecules"
        ... )

        With hints and formatting:
        >>> create_cloze_card(
        ...     text=(
        ...         "The {{c1::pythagorean theorem::a<sup>2</sup> + b<sup>2</sup>}} "
        ...         "states that a<sup>2</sup> + b<sup>2</sup> = c<sup>2</sup>."
        ...     ),
        ...     extra="<i>Named after the Greek mathematician Pythagoras</i>",
        ...     deck="Math::Geometry"
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

    **HTML Formatting:** The front field supports full HTML formatting. The back field
    (typed answer) should typically be plain text since it's used for exact matching,
    but HTML is supported if needed.

    Args:
        front: Question or prompt text (supports HTML)
        back: Expected typed answer (must match exactly - typically plain text)
        deck: Deck name (uses default if not specified)
        tags: List of tags to apply to the card
        validate: Whether to run quality validation (default: True)

    Returns:
        Success message with note ID and any validation warnings, or error message

    Examples:
        Basic usage:
        >>> create_type_in_card(
        ...     front="Chemical symbol for gold",
        ...     back="Au",
        ...     deck="Chemistry::Elements"
        ... )

        With HTML formatting:
        >>> create_type_in_card(
        ...     front="Type the name of this compound: H<sub>2</sub>SO<sub>4</sub>",
        ...     back="sulfuric acid",
        ...     deck="Chemistry::Nomenclature"
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


@app.tool()
async def update_card_tags(
    note_id: int,
    tags_to_add: list[str] | None = None,
    tags_to_remove: list[str] | None = None,
) -> CallToolResult:
    """Update tags on an existing Anki note.

    Allows adding new tags and/or removing existing tags from a note.
    At least one of tags_to_add or tags_to_remove must be provided.

    Args:
        note_id: The Anki note ID to update
        tags_to_add: List of tags to add to the note
        tags_to_remove: List of tags to remove from the note

    Returns:
        Success message with current tags, or error message

    Examples:
        Add tags only:
        >>> update_card_tags(
        ...     note_id=1767644643572,
        ...     tags_to_add=["course_01", "important"]
        ... )

        Remove tags only:
        >>> update_card_tags(
        ...     note_id=1767644643572,
        ...     tags_to_remove=["old_tag"]
        ... )

        Add and remove tags:
        >>> update_card_tags(
        ...     note_id=1767644643572,
        ...     tags_to_add=["course_01", "module_02"],
        ...     tags_to_remove=["deprecated"]
        ... )
    """
    try:
        # Validate inputs
        if not tags_to_add and not tags_to_remove:
            return CallToolResult(
                isError=True,
                content=[
                    TextContent(
                        type="text",
                        text="At least one of tags_to_add or tags_to_remove must be provided.",
                    )
                ],
            )

        client = get_anki_client()

        # Add tags if requested
        if tags_to_add:
            tags_str = " ".join(tags_to_add)
            await client.add_tags([note_id], tags_str)

        # Remove tags if requested
        if tags_to_remove:
            tags_str = " ".join(tags_to_remove)
            await client.remove_tags([note_id], tags_str)

        # Get updated tags
        updated_tags = await client.get_note_tags(note_id)

        # Build response message
        msg = f"Tags updated successfully for note ID {note_id}\n\n"

        if tags_to_add:
            msg += f"Added tags: {', '.join(tags_to_add)}\n"
        if tags_to_remove:
            msg += f"Removed tags: {', '.join(tags_to_remove)}\n"

        msg += f"\nCurrent tags: {', '.join(updated_tags) if updated_tags else '(no tags)'}"

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
