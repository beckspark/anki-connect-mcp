"""MCP tools for creating and managing Anki flashcards."""

import re

from mcp.types import CallToolResult, TextContent

from ..client import AnkiConnectionError, get_anki_client
from ..config import settings
from ..db import get_database
from ..formatting import get_text_length, highlight_code_blocks, strip_html
from ..models import BasicCard, ClozeCard, TypeInCard
from ..server import app


@app.tool()
async def create_basic_card(
    front: str,
    back: str,
    deck: str | None = None,
    tags: list[str] | None = None,
) -> CallToolResult:
    """Create a basic flashcard with front and back sides.

    Creates a traditional flashcard with a question/prompt on the front and answer on the back.
    The LLM is responsible for quality judgment - this tool simply creates the card.

    **HTML Formatting:** Both front and back fields support full HTML formatting. You can use:
    - Basic formatting: `<b>bold</b>`, `<i>italic</i>`, `<u>underline</u>`
    - Colors: `<span style="color: red;">text</span>`
    - Lists: `<ul><li>item</li></ul>` or `<ol><li>item</li></ol>`
    - Line breaks: `<br>`
    - Any other standard HTML tags

    **Syntax Highlighting:** Multi-line code wrapped in
    `<pre><code class="language-X">...</code></pre>` is automatically
    syntax-highlighted using Pygments (monokai theme, inline styles).
    Use inline `<code>` for short expressions (not highlighted).

    For convenience, use the formatting module helpers or pass HTML directly as strings.

    Args:
        front: Question or prompt text (max 1000 chars visible text, HTML tags not counted)
        back: Answer text (max 2000 chars visible text, HTML tags not counted)
        deck: Deck name (uses default if not specified). Supports hierarchy with ::
              (e.g., "Biology::Cells")
        tags: List of tags to apply to the card

    Returns:
        Success message with note ID, or error message

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
        # Create card model (validates basic constraints like min/max length)
        card = BasicCard(
            front=front, back=back, deck=deck or settings.default_deck, tags=tags or []
        )

        # Create note in Anki
        client = get_anki_client()
        note = {
            "deckName": card.deck,
            "modelName": "Basic",
            "fields": {"Front": card.front, "Back": card.back},
            "tags": card.tags,
        }

        # Auto-highlight code blocks in all fields
        for field_name in note["fields"]:
            note["fields"][field_name] = highlight_code_blocks(note["fields"][field_name])

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
        )

        # Build response message
        msg = f"Card created successfully (Anki note ID: {note_id})\n\nDeck: {card.deck}"

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
) -> CallToolResult:
    """Create a cloze deletion flashcard.

    Cloze deletions are fill-in-the-blank style cards. Research shows they're more effective
    for factual learning than basic cards. Use {{c1::text}} format for deletions.
    The LLM is responsible for quality judgment - this tool simply creates the card.

    **HTML Formatting:** Cloze cards support full HTML formatting both inside and outside
    cloze deletions. You can combine cloze syntax with HTML tags seamlessly.

    **Syntax Highlighting:** Multi-line code wrapped in
    `<pre><code class="language-X">...</code></pre>` is automatically
    syntax-highlighted using Pygments (monokai theme, inline styles).
    Use inline `<code>` for short expressions (not highlighted).

    Args:
        text: Text with cloze deletions. Format: {{c1::answer}} or {{c1::answer::hint}}
              Use c1, c2, c3, etc. for multiple deletions. HTML tags are supported.
        deck: Deck name (uses default if not specified)
        tags: List of tags to apply to the card
        extra: Additional context or hints shown on all cards (supports HTML)

    Returns:
        Success message with note ID, or error message

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
        # Create card model
        card = ClozeCard(
            text=text,
            deck=deck or settings.default_deck,
            tags=tags or [],
            extra=extra,
        )

        # Validate cloze format (this is structural, not quality judgment)
        if not re.search(r"\{\{c\d+::", card.text):
            return CallToolResult(
                isError=True,
                content=[
                    TextContent(
                        type="text",
                        text="Cloze card must contain at least one cloze deletion "
                        "in {{c1::text}} format.",
                    )
                ],
            )

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

        # Auto-highlight code blocks in all fields
        for field_name in note["fields"]:
            note["fields"][field_name] = highlight_code_blocks(note["fields"][field_name])

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
        )

        # Build response message
        msg = f"Cloze card created successfully (Anki note ID: {note_id})\n\nDeck: {card.deck}"

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
) -> CallToolResult:
    """Create a type-in answer flashcard.

    Type-in cards require typing the exact answer, testing recall more rigorously than
    basic cards. Best for learning precise terms, spellings, or short definitions.
    The LLM is responsible for quality judgment - this tool simply creates the card.

    **HTML Formatting:** The front field supports full HTML formatting. The back field
    (typed answer) should typically be plain text since it's used for exact matching,
    but HTML is supported if needed.

    **Syntax Highlighting:** Multi-line code wrapped in
    `<pre><code class="language-X">...</code></pre>` is automatically
    syntax-highlighted using Pygments (monokai theme, inline styles).
    Use inline `<code>` for short expressions (not highlighted).

    Args:
        front: Question or prompt text (supports HTML)
        back: Expected typed answer (must match exactly - typically plain text)
        deck: Deck name (uses default if not specified)
        tags: List of tags to apply to the card

    Returns:
        Success message with note ID, or error message

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
        # Create card model
        card = TypeInCard(
            front=front, back=back, deck=deck or settings.default_deck, tags=tags or []
        )

        # Create note in Anki
        client = get_anki_client()
        note = {
            "deckName": card.deck,
            "modelName": "Basic (type in the answer)",
            "fields": {"Front": card.front, "Back": card.back},
            "tags": card.tags,
        }

        # Auto-highlight code blocks in all fields
        for field_name in note["fields"]:
            note["fields"][field_name] = highlight_code_blocks(note["fields"][field_name])

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
        )

        # Build response message
        msg = f"Type-in card created successfully (Anki note ID: {note_id})\n\nDeck: {card.deck}"

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


@app.tool()
async def delete_card(note_id: int) -> CallToolResult:
    """Delete an Anki card (note) permanently.

    This permanently removes the note and all associated cards from Anki.
    This action cannot be undone.

    Args:
        note_id: The Anki note ID to delete

    Returns:
        Success confirmation, or error message

    Examples:
        Delete a single card:
        >>> delete_card(note_id=1768502042387)
    """
    try:
        client = get_anki_client()

        # Verify note exists before deleting
        note_info = await client.notes_info([note_id])
        if not note_info or not note_info[0]:
            return CallToolResult(
                isError=True,
                content=[
                    TextContent(
                        type="text",
                        text=f"Note ID {note_id} not found. It may have already been deleted.",
                    )
                ],
            )

        # Delete the note
        await client.delete_notes([note_id])

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Successfully deleted note ID {note_id}",
                )
            ]
        )

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
async def inspect_card_structure(
    front: str | None = None,
    back: str | None = None,
    text: str | None = None,
    extra: str | None = None,
    card_type: str = "basic",
) -> CallToolResult:
    """Inspect the structural properties of a card draft.

    Returns raw structural data (word counts, cloze counts, field lengths, etc.)
    without making quality judgments. The LLM can use this data to inform
    its own quality assessment based on context and learning goals.

    This tool provides data for reflection, NOT verdicts. Use your judgment
    about what makes a good card for the specific learning context.

    Args:
        front: Front of basic/type-in card (required for basic/type_in)
        back: Back of basic/type-in card (required for basic/type_in)
        text: Text of cloze card with {{c1::deletions}} (required for cloze)
        extra: Additional context for cloze cards (optional)
        card_type: Card type - "basic", "cloze", or "type_in" (default: "basic")

    Returns:
        Structural data about the card for LLM reflection

    Examples:
        Inspect a basic card:
        >>> inspect_card_structure(
        ...     front="What is the capital of France?",
        ...     back="Paris",
        ...     card_type="basic"
        ... )

        Inspect a cloze card:
        >>> inspect_card_structure(
        ...     text="The {{c1::mitochondria}} is the {{c2::powerhouse}} of the cell.",
        ...     card_type="cloze"
        ... )
    """
    try:
        # Validate card_type parameter
        valid_types = ["basic", "cloze", "type_in"]
        if card_type not in valid_types:
            valid_list = ", ".join(valid_types)
            return CallToolResult(
                isError=True,
                content=[
                    TextContent(
                        type="text",
                        text=f"Invalid card_type '{card_type}'. Must be one of: {valid_list}",
                    )
                ],
            )

        # Build structural analysis based on card type
        structure: dict[str, str | int | float | bool | list[str]] = {
            "card_type": card_type,
        }

        if card_type in ["basic", "type_in"]:
            if not front or not back:
                return CallToolResult(
                    isError=True,
                    content=[
                        TextContent(
                            type="text",
                            text=f"For {card_type} cards, both 'front' and 'back' "
                            "parameters are required.",
                        )
                    ],
                )

            # Front field analysis
            front_plain = strip_html(front)
            front_words = len(front_plain.split())
            structure["front_word_count"] = front_words
            structure["front_char_count"] = get_text_length(front)
            structure["front_has_html"] = front != front_plain
            structure["front_has_question_mark"] = "?" in front

            # Back field analysis
            back_plain = strip_html(back)
            back_words = len(back_plain.split())
            structure["back_word_count"] = back_words
            structure["back_char_count"] = get_text_length(back)
            structure["back_has_html"] = back != back_plain

        elif card_type == "cloze":
            if not text:
                return CallToolResult(
                    isError=True,
                    content=[
                        TextContent(
                            type="text",
                            text="For cloze cards, the 'text' parameter is required.",
                        )
                    ],
                )

            # Cloze analysis
            cloze_deletions = re.findall(r"\{\{c(\d+)::", text)
            unique_cloze_numbers = sorted(set(int(n) for n in cloze_deletions))
            structure["cloze_count"] = len(cloze_deletions)
            structure["unique_cloze_numbers"] = [str(n) for n in unique_cloze_numbers]
            structure["has_valid_cloze_format"] = len(cloze_deletions) > 0

            # Text analysis (without cloze syntax)
            text_plain = strip_html(text.replace("{{", "").replace("}}", ""))
            structure["text_word_count"] = len(text_plain.split())
            structure["text_char_count"] = len(text_plain)
            structure["text_has_html"] = text != strip_html(text)

            # Extra field if provided
            if extra:
                extra_plain = strip_html(extra)
                structure["extra_word_count"] = len(extra_plain.split())
                structure["extra_has_html"] = extra != extra_plain

        # Format response
        msg = f"Card Structure Analysis ({card_type}):\n\n"
        for key, value in structure.items():
            readable_key = key.replace("_", " ").title()
            msg += f"  {readable_key}: {value}\n"

        msg += "\nThis is raw structural data. Use your judgment about quality "
        msg += "based on the specific learning context and goals."

        return CallToolResult(content=[TextContent(type="text", text=msg)])

    except Exception as e:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Unexpected error: {str(e)}")],
        )
