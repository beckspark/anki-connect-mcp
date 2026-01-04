"""MCP tools for managing Anki decks."""

from mcp.types import CallToolResult, TextContent

from ..client import AnkiConnectionError, get_anki_client
from ..server import app


@app.tool()
async def list_decks() -> CallToolResult:
    """List all available Anki decks.

    Returns all deck names from your Anki collection, including hierarchical decks
    (displayed with :: separators, e.g., "Biology::Cells").

    Returns:
        List of deck names or error message

    Example:
        >>> list_decks()
        Available decks:
        - Default
        - Biology
        - Biology::Cells
        - Biology::Genetics
        - Chemistry
    """
    try:
        client = get_anki_client()
        deck_names = await client.deck_names()

        if not deck_names:
            return CallToolResult(
                content=[TextContent(type="text", text="No decks found in Anki collection.")]
            )

        # Sort decks alphabetically for better readability
        deck_names_sorted = sorted(deck_names)

        deck_list = "\n".join(f"- {name}" for name in deck_names_sorted)
        message = f"Available decks ({len(deck_names_sorted)} total):\n\n{deck_list}"

        return CallToolResult(content=[TextContent(type="text", text=message)])

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
async def create_deck(name: str) -> CallToolResult:
    """Create a new Anki deck.

    Creates a new deck in your Anki collection. Supports hierarchical deck structure
    using :: separators (e.g., "Biology::Cells" creates a "Cells" subdeck under "Biology").
    If parent decks don't exist, they will be created automatically.

    Args:
        name: Deck name. Use :: for hierarchy (e.g., "Subject::Topic::Subtopic")

    Returns:
        Success message with deck ID or error message

    Example:
        >>> create_deck("Biology::Molecular Biology")
        Deck created successfully: Biology::Molecular Biology (ID: 1234567890)
    """
    try:
        # Validate deck name
        if not name or not name.strip():
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text="Deck name cannot be empty.")],
            )

        name = name.strip()

        # Check if deck already exists
        client = get_anki_client()
        existing_decks = await client.deck_names()

        if name in existing_decks:
            return CallToolResult(
                isError=True,
                content=[
                    TextContent(
                        type="text",
                        text=(
                            f"Deck '{name}' already exists. "
                            "Use a different name or manage the existing deck."
                        ),
                    )
                ],
            )

        # Create deck
        deck_id = await client.create_deck(name)

        message = f"Deck created successfully: {name} (ID: {deck_id})"

        # Add helpful note about hierarchy if deck name contains ::
        if "::" in name:
            parts = name.split("::")
            message += f"\n\nHierarchy: {' → '.join(parts)}"

        return CallToolResult(content=[TextContent(type="text", text=message)])

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
async def get_deck_stats(deck_name: str) -> CallToolResult:
    """Get statistics for an Anki deck.

    Retrieves learning statistics including counts of new, learning, and review cards
    for the specified deck. Useful for tracking study progress and workload.

    Args:
        deck_name: Name of the deck to get statistics for

    Returns:
        Deck statistics or error message

    Example:
        >>> get_deck_stats("Biology::Cells")
        Statistics for deck: Biology::Cells

        New cards: 42
        Learning: 15
        Review: 128
        Total cards: 185
    """
    try:
        # Validate deck name
        if not deck_name or not deck_name.strip():
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text="Deck name cannot be empty.")],
            )

        deck_name = deck_name.strip()

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

        # Get deck statistics
        stats = await client.get_deck_stats(deck_name)

        # Extract stats from the response
        # AnkiConnect returns a dict with the deck name as key
        deck_stats = stats.get(deck_name, {})

        if not deck_stats:
            return CallToolResult(
                isError=True,
                content=[
                    TextContent(
                        type="text",
                        text=f"Unable to retrieve statistics for deck '{deck_name}'.",
                    )
                ],
            )

        # Format the statistics
        new_count = deck_stats.get("new_count", 0)
        learn_count = deck_stats.get("learn_count", 0)
        review_count = deck_stats.get("review_count", 0)
        total_cards = deck_stats.get("total_in_deck", 0)

        message = f"Statistics for deck: {deck_name}\n\n"
        message += f"New cards: {new_count}\n"
        message += f"Learning: {learn_count}\n"
        message += f"Review: {review_count}\n"
        message += f"Total cards: {total_cards}"

        # Add workload assessment
        daily_workload = new_count + learn_count + review_count
        if daily_workload > 0:
            message += f"\n\nToday's workload: {daily_workload} cards"

        return CallToolResult(content=[TextContent(type="text", text=message)])

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
