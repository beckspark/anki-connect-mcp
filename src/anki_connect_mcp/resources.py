"""MCP resources for read-only data access (history, statistics)."""

from .db import get_database
from .server import app


@app.resource("card-history://recent")
async def card_history() -> str:
    """Recent card creation history.

    Provides read-only access to the 50 most recently created flashcards,
    including their source, deck, and creation time.

    Returns:
        Formatted table of recent card history
    """
    db = get_database()
    cards = db.get_recent_cards(limit=50)

    if not cards:
        return "No cards have been created yet."

    # Format as table
    output = "Recent Card Creation History (50 most recent)\n"
    output += "=" * 80 + "\n\n"

    for card in cards:
        card_type = card["card_type"].upper()
        front_text = (
            card["front_or_text"][:50] + "..."
            if len(card["front_or_text"]) > 50
            else card["front_or_text"]
        )
        deck = card["deck"]
        source = card["source_type"] or "manual"
        created = card["created_at"]

        output += f"[{card_type}] {front_text}\n"
        output += f"  Deck: {deck} | Source: {source} | Created: {created}\n"
        output += f"  Anki Note ID: {card['anki_note_id']}\n\n"

    return output


@app.resource("card-history://source/{source_path}")
async def cards_by_source(source_path: str) -> str:
    """Cards generated from a specific source.

    Provides read-only access to all cards created from a particular PDF, ePub,
    or other source file.

    Args:
        source_path: Path or URL of the source

    Returns:
        Formatted list of cards from this source
    """
    db = get_database()
    cards = db.get_cards_by_source(source_path)

    if not cards:
        return (
            f"No cards found from source: {source_path}\n\n"
            "This source may not exist or no cards have been generated from it yet."
        )

    # Format output
    output = f"Cards Generated from: {source_path}\n"
    output += "=" * 80 + "\n"
    output += f"Total cards: {len(cards)}\n\n"

    for idx, card in enumerate(cards, 1):
        card_type = card["card_type"].upper()
        front_text = card["front_or_text"]
        deck = card["deck"]
        created = card["created_at"]

        output += f"{idx}. [{card_type}] {front_text}\n"
        if card["back"]:
            output += (
                f"   Answer: {card['back'][:100]}...\n"
                if len(card["back"]) > 100
                else f"   Answer: {card['back']}\n"
            )
        output += f"   Deck: {deck} | Created: {created}\n"

        # Show validation warnings if any
        if card["validation_warnings"]:
            output += f"   Warnings: {card['validation_warnings']}\n"

        output += "\n"

    return output


@app.resource("card-history://stats")
async def validation_stats() -> str:
    """Aggregated validation statistics.

    Provides read-only access to validation statistics across all generated cards,
    showing common warning patterns and quality metrics.

    Returns:
        Formatted validation statistics
    """
    db = get_database()
    stats = db.get_validation_stats()

    output = "Flashcard Quality Statistics\n"
    output += "=" * 80 + "\n\n"

    total = stats["total_cards"]
    with_warnings = stats["cards_with_warnings"]
    warning_rate = stats["warning_rate"]

    output += f"Total cards created: {total}\n"
    output += f"Cards with validation warnings: {with_warnings} ({warning_rate}%)\n"
    output += f"Cards with no warnings: {total - with_warnings} ({100 - warning_rate:.2f}%)\n\n"

    if total > 0:
        output += "Quality Score: "
        if warning_rate < 10:
            output += "Excellent ✓\n"
        elif warning_rate < 25:
            output += "Good\n"
        elif warning_rate < 50:
            output += "Fair - Consider reviewing card design\n"
        else:
            output += "Needs Improvement - Many cards violate best practices\n"

        output += "\nRecommendations:\n"
        output += "- Review cards with warnings for quality improvements\n"
        output += "- Follow minimum information principle (one concept per card)\n"
        output += "- Keep answers concise (<50 words)\n"
        output += "- Use cloze deletions for factual learning\n"
    else:
        output += "No cards created yet. Start creating flashcards to see statistics!\n"

    return output


@app.resource("card-history://generation-history")
async def generation_history() -> str:
    """Generation session history.

    Provides read-only access to all generation sessions, showing which sources
    were used to create cards and when.

    Returns:
        Formatted generation history
    """
    db = get_database()
    generations = db.get_generation_history(limit=100)

    if not generations:
        return "No generation sessions recorded yet."

    output = "Card Generation History (100 most recent sessions)\n"
    output += "=" * 80 + "\n\n"

    for gen in generations:
        gen_id = gen["id"]
        source_type = gen["source_type"]
        source_path = gen["source_path"] or "N/A"
        card_count = gen["card_count"]
        created = gen["generated_at"]

        output += f"Session #{gen_id} [{source_type.upper()}]\n"
        output += f"  Source: {source_path}\n"
        output += f"  Cards created: {card_count}\n"
        output += f"  Date: {created}\n\n"

    return output
