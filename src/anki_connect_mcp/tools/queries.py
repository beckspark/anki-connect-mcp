"""MCP tools for querying and inspecting Anki cards."""

from collections import Counter

from mcp.types import CallToolResult, TextContent

from ..client import AnkiConnectionError, get_anki_client
from ..server import app


@app.tool()
async def search_deck_cards(
    deck_name: str,
    search_query: str | None = None,
    tags: list[str] | None = None,
    limit: int = 20,
) -> CallToolResult:
    """Find and list cards in a deck with optional filtering.

    Searches for cards within a specific deck and displays their content, tags, and type.
    Useful for inspecting existing cards before creating new ones.

    Args:
        deck_name: Name of the deck to search
        search_query: Optional Anki search syntax (e.g., "is:new", "rated:7")
        tags: Optional list of tags to filter by
        limit: Maximum number of cards to return (default: 20, max: 100)

    Returns:
        List of cards with previews, or error message

    Examples:
        Search all cards in a deck:
        >>> search_deck_cards("Biology::Cells", limit=10)

        Filter by tags:
        >>> search_deck_cards("Chemistry", tags=["organic", "reactions"])

        Combine with search query:
        >>> search_deck_cards("Math", search_query="is:new", limit=5)
    """
    try:
        # Validate inputs
        if limit > 100:
            return CallToolResult(
                isError=True,
                content=[
                    TextContent(
                        type="text",
                        text="Limit cannot exceed 100 cards. Please use a smaller limit.",
                    )
                ],
            )

        # Check if deck exists
        client = get_anki_client()
        existing_decks = await client.deck_names()

        if deck_name not in existing_decks:
            # Provide helpful suggestions
            suggestions = [d for d in existing_decks if deck_name.lower() in d.lower()]
            error_msg = f"Deck '{deck_name}' not found."

            if suggestions:
                error_msg += "\n\nDid you mean one of these?"
                error_msg += "\n" + "\n".join(f"- {s}" for s in suggestions[:5])
            else:
                error_msg += "\n\nUse list_decks to see all available decks."

            return CallToolResult(isError=True, content=[TextContent(type="text", text=error_msg)])

        # Build Anki search query
        query_parts = [f'deck:"{deck_name}"']

        if tags:
            for tag in tags:
                query_parts.append(f'tag:"{tag}"')

        if search_query:
            query_parts.append(search_query)

        query = " ".join(query_parts)

        # Find cards
        card_ids = await client.find_cards(query)

        if not card_ids:
            msg = f"No cards found in deck '{deck_name}'"
            if tags or search_query:
                msg += " matching the filters"
            msg += "."

            if tags or search_query:
                msg += "\n\nTry removing some filters or use search_deck_cards with just the deck name."

            return CallToolResult(content=[TextContent(type="text", text=msg)])

        # Limit results
        total_found = len(card_ids)
        card_ids = card_ids[:limit]

        # Get card details
        cards_info = await client.cards_info(card_ids)

        # Get note IDs and fetch note details
        note_ids = list({card["note"] for card in cards_info})
        notes_info = await client.notes_info(note_ids)

        # Create note ID to note info mapping
        note_map = {note["noteId"]: note for note in notes_info}

        # Build response
        showing_text = f"showing {len(card_ids)}" if total_found > limit else f"showing all {len(card_ids)}"
        msg = f"Found {total_found} cards in deck \"{deck_name}\" ({showing_text})\n\n"

        for idx, card in enumerate(cards_info, 1):
            note_id = card["note"]
            note = note_map.get(note_id, {})

            model_name = note.get("modelName", "Unknown")
            note_tags = note.get("tags", [])
            fields = note.get("fields", {})

            msg += f"Card {idx} - Note ID: {note_id}\n"
            msg += f"Type: {model_name}\n"
            msg += f"Tags: {', '.join(note_tags) if note_tags else '(no tags)'}\n"

            # Preview fields based on note type
            if model_name == "Basic" or model_name == "Basic (type in the answer)":
                front = fields.get("Front", {}).get("value", "")
                back = fields.get("Back", {}).get("value", "")

                # Truncate for preview
                front_preview = (front[:80] + "...") if len(front) > 80 else front
                back_preview = (back[:80] + "...") if len(back) > 80 else back

                msg += f'Preview: "{front_preview}" → "{back_preview}"\n'

            elif model_name == "Cloze":
                text = fields.get("Text", {}).get("value", "")
                text_preview = (text[:100] + "...") if len(text) > 100 else text
                msg += f'Text: "{text_preview}"\n'

            else:
                # Generic handling for other note types
                field_values = [f.get("value", "") for f in fields.values()]
                if field_values:
                    first_field = field_values[0]
                    preview = (first_field[:100] + "...") if len(first_field) > 100 else first_field
                    msg += f'Preview: "{preview}"\n'

            msg += "\n"

        return CallToolResult(content=[TextContent(type="text", text=msg.strip())])

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
async def inspect_card(note_id: int) -> CallToolResult:
    """View complete details of a specific card.

    Displays all fields, tags, deck, and metadata for a single note.
    Shows raw HTML formatting to understand card structure.

    Args:
        note_id: The Anki note ID to inspect

    Returns:
        Complete card details, or error message

    Examples:
        >>> inspect_card(1767551176400)
    """
    try:
        client = get_anki_client()

        # Get note info
        notes = await client.notes_info([note_id])

        if not notes or not notes[0]:
            return CallToolResult(
                isError=True,
                content=[
                    TextContent(
                        type="text",
                        text=(
                            f"Note ID {note_id} not found.\n\n"
                            "Use search_deck_cards to find cards and their note IDs."
                        ),
                    )
                ],
            )

        note = notes[0]

        # Extract note details
        model_name = note.get("modelName", "Unknown")
        note_tags = note.get("tags", [])
        fields = note.get("fields", {})

        # Build response
        msg = f"Note ID: {note_id}\n"
        msg += f"Type: {model_name}\n"

        # Get deck name (from first card)
        card_ids = await client.find_cards(f"nid:{note_id}")
        if card_ids:
            cards = await client.cards_info(card_ids)
            if cards:
                msg += f"Deck: {cards[0].get('deckName', 'Unknown')}\n"

        msg += f"Tags: {', '.join(note_tags) if note_tags else '(no tags)'}\n\n"

        # Display fields
        msg += "Fields:\n"
        for field_name, field_data in fields.items():
            field_value = field_data.get("value", "")
            msg += f"  {field_name}: {field_value}\n"

        # Show card generation info
        if card_ids:
            msg += f"\nCards Generated: {len(card_ids)}\n"

        return CallToolResult(content=[TextContent(type="text", text=msg.strip())])

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
async def preview_deck_patterns(
    deck_name: str,
    sample_size: int = 10,
) -> CallToolResult:
    """Analyze existing card patterns in a deck.

    Examines a sample of cards to understand formatting, tagging, and content patterns.
    Useful before creating new cards to match the existing style.

    Args:
        deck_name: Deck to analyze
        sample_size: Number of sample cards to show (default: 10, max: 25)

    Returns:
        Deck analysis with patterns and samples, or error message

    Examples:
        >>> preview_deck_patterns("Biology::Cells")

        Larger sample:
        >>> preview_deck_patterns("Chemistry", sample_size=20)
    """
    try:
        # Validate inputs
        if sample_size > 25:
            return CallToolResult(
                isError=True,
                content=[
                    TextContent(
                        type="text",
                        text="Sample size cannot exceed 25 cards. Please use a smaller sample size.",
                    )
                ],
            )

        # Check if deck exists
        client = get_anki_client()
        existing_decks = await client.deck_names()

        if deck_name not in existing_decks:
            suggestions = [d for d in existing_decks if deck_name.lower() in d.lower()]
            error_msg = f"Deck '{deck_name}' not found."

            if suggestions:
                error_msg += "\n\nDid you mean one of these?"
                error_msg += "\n" + "\n".join(f"- {s}" for s in suggestions[:5])
            else:
                error_msg += "\n\nUse list_decks to see all available decks."

            return CallToolResult(isError=True, content=[TextContent(type="text", text=error_msg)])

        # Find all cards in deck
        card_ids = await client.find_cards(f'deck:"{deck_name}"')

        if not card_ids:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Deck '{deck_name}' is empty. No cards to analyze.",
                    )
                ]
            )

        total_cards = len(card_ids)

        # Sample cards (take first N or all if fewer)
        sample_card_ids = card_ids[: min(sample_size, total_cards)]

        # Get card and note details
        cards_info = await client.cards_info(sample_card_ids)
        note_ids = list({card["note"] for card in cards_info})
        notes_info = await client.notes_info(note_ids)

        # Analyze patterns
        model_counter = Counter()
        tag_counter: Counter[str] = Counter()
        html_usage = 0
        field_lengths = []

        for note in notes_info:
            model_name = note.get("modelName", "Unknown")
            model_counter[model_name] += 1

            # Count tags
            tags = note.get("tags", [])
            for tag in tags:
                tag_counter[tag] += 1

            # Analyze fields
            fields = note.get("fields", {})
            for field_data in fields.values():
                field_value = field_data.get("value", "")

                # Check for HTML
                if any(tag in field_value for tag in ["<b>", "<i>", "<br>", "<sub>", "<sup>", "<ul>", "<ol>"]):
                    html_usage += 1
                    break  # Count once per note

                field_lengths.append(len(field_value))

        # Build response
        msg = f"Deck Analysis: \"{deck_name}\"\n"
        msg += f"Total Cards: {total_cards}\n\n"

        # Card type distribution
        msg += "Card Type Distribution:\n"
        for model, count in model_counter.most_common():
            percentage = (count / len(notes_info)) * 100
            msg += f"- {model}: {count} ({percentage:.0f}%)\n"
        msg += "\n"

        # Common tags
        if tag_counter:
            msg += f"Common Tags (top {min(5, len(tag_counter))}):\n"
            for idx, (tag, count) in enumerate(tag_counter.most_common(5), 1):
                msg += f"{idx}. {tag} ({count} cards)\n"
            msg += "\n"

        # Formatting patterns
        msg += "Formatting Patterns:\n"
        if html_usage > 0:
            html_percentage = (html_usage / len(notes_info)) * 100
            msg += f"- {html_percentage:.0f}% of cards use HTML formatting\n"
        else:
            msg += "- No HTML formatting detected in sample\n"

        if field_lengths:
            avg_length = sum(field_lengths) / len(field_lengths)
            msg += f"- Average field length: {avg_length:.0f} characters\n"

        msg += f"\nSample Cards (showing {len(notes_info)}):\n\n"

        # Show sample cards
        note_map = {note["noteId"]: note for note in notes_info}

        for idx, card in enumerate(cards_info[:sample_size], 1):
            note_id = card["note"]
            note = note_map.get(note_id, {})

            if not note:
                continue

            model_name = note.get("modelName", "Unknown")
            note_tags = note.get("tags", [])
            fields = note.get("fields", {})

            msg += f"[Card {idx}] {model_name}\n"
            msg += f"Tags: {', '.join(note_tags) if note_tags else '(no tags)'}\n"

            # Show fields based on type
            if model_name == "Basic" or model_name == "Basic (type in the answer)":
                front = fields.get("Front", {}).get("value", "")
                back = fields.get("Back", {}).get("value", "")
                msg += f"Front: {front}\n"
                msg += f"Back: {back}\n"

            elif model_name == "Cloze":
                text = fields.get("Text", {}).get("value", "")
                msg += f"Text: {text}\n"

            else:
                # Generic handling
                for field_name, field_data in fields.items():
                    field_value = field_data.get("value", "")
                    msg += f"{field_name}: {field_value}\n"

            msg += "\n"

        return CallToolResult(content=[TextContent(type="text", text=msg.strip())])

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
