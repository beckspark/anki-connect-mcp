"""MCP tools for deck analysis - raw data for LLM judgment.

These tools provide structural and performance data about decks.
The LLM is responsible for interpreting this data and making quality judgments
based on the specific learning context and goals.

Philosophy: Tools provide data, LLM provides wisdom.
"""

import re
from collections import Counter

from mcp.types import CallToolResult, TextContent

from ..client import AnkiConnectionError, get_anki_client
from ..db.database import get_database
from ..formatting import strip_html
from ..server import app


@app.tool()
async def analyze_deck_quality(
    deck_name: str,
    sample_size: int | None = None,
    include_card_details: bool = False,
) -> CallToolResult:
    """Get structural quality data for a deck.

    Returns raw structural data about deck composition, patterns, and card characteristics.
    The LLM interprets this data based on learning context - no automatic scoring.

    Args:
        deck_name: Name of the deck to analyze
        sample_size: Optional sample size (None = analyze all cards)
        include_card_details: Include detailed card-level data (default: False)

    Returns:
        Raw structural data about the deck for LLM analysis

    Examples:
        Quick health check:
        >>> analyze_deck_quality("Biology::Cells")

        Sample analysis for large decks:
        >>> analyze_deck_quality("Chemistry", sample_size=100)

        With problematic card details:
        >>> analyze_deck_quality("Math", include_card_details=True)
    """
    try:
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

        # Fetch all cards in deck
        card_ids = await client.find_cards(f'deck:"{deck_name}"')

        if not card_ids:
            msg = f"Deck '{deck_name}' is empty (0 cards).\n\n"
            msg += "No structural data to analyze."
            return CallToolResult(content=[TextContent(type="text", text=msg)])

        # Sample if requested
        import random

        original_count = len(card_ids)
        if sample_size and sample_size < len(card_ids):
            card_ids = random.sample(card_ids, sample_size)

        # Get note details
        cards_info = await client.cards_info(card_ids)
        note_ids = list({card["note"] for card in cards_info})
        notes_info = await client.notes_info(note_ids)

        # Analyze structural patterns
        type_counter: Counter[str] = Counter()
        tag_usage = 0
        html_usage = 0
        field_lengths: list[int] = []
        word_counts: list[int] = []
        cloze_counts: list[int] = []
        card_details: list[dict[str, str | int | list[str]]] = []

        html_tags = [
            "<b>",
            "<i>",
            "<u>",
            "<br>",
            "<sub>",
            "<sup>",
            "<ul>",
            "<ol>",
            "<div>",
            "<span>",
        ]

        for note in notes_info:
            model_name = note.get("modelName", "Unknown")
            type_counter[model_name] += 1

            tags = note.get("tags", [])
            if tags:
                tag_usage += 1

            fields = note.get("fields", {})
            note_has_html = False

            for field_data in fields.values():
                field_value = field_data.get("value", "")

                # Check for HTML
                if any(tag in field_value for tag in html_tags):
                    note_has_html = True

                # Track field length
                clean_text = strip_html(field_value)
                field_lengths.append(len(clean_text))
                word_counts.append(len(clean_text.split()))

                # Count cloze deletions
                cloze_matches = re.findall(r"\{\{c\d+::", field_value)
                if cloze_matches:
                    cloze_counts.append(len(cloze_matches))

            if note_has_html:
                html_usage += 1

            # Collect card details if requested
            if include_card_details:
                detail: dict[str, str | int | list[str]] = {
                    "note_id": note["noteId"],
                    "model": model_name,
                    "tags": tags,
                }
                # Add first field preview
                first_field = list(fields.values())[0] if fields else {}
                first_value = first_field.get("value", "")
                preview = strip_html(first_value)[:100]
                if len(first_value) > 100:
                    preview += "..."
                detail["preview"] = preview
                card_details.append(detail)

        # Build response
        total_cards = len(notes_info)
        msg = f"Deck Structure Analysis: '{deck_name}'\n"
        if sample_size and sample_size < original_count:
            msg += f"(Sample of {total_cards} from {original_count} total cards)\n"
        msg += "\n"

        # Basic counts
        msg += f"Total Cards: {total_cards}\n"
        msg += f"Cards with Tags: {tag_usage} ({tag_usage / total_cards * 100:.0f}%)\n"
        msg += f"Cards with HTML: {html_usage} ({html_usage / total_cards * 100:.0f}%)\n\n"

        # Card type distribution
        msg += "Card Type Distribution:\n"
        for card_type, count in type_counter.most_common():
            pct = count / total_cards * 100
            msg += f"  {card_type}: {count} ({pct:.0f}%)\n"
        msg += "\n"

        # Field statistics
        if field_lengths:
            avg_field_len = sum(field_lengths) / len(field_lengths)
            max_field_len = max(field_lengths)
            min_field_len = min(field_lengths)
            msg += "Field Length Stats (characters):\n"
            msg += f"  Average: {avg_field_len:.0f}\n"
            msg += f"  Min: {min_field_len}\n"
            msg += f"  Max: {max_field_len}\n\n"

        if word_counts:
            avg_words = sum(word_counts) / len(word_counts)
            max_words = max(word_counts)
            msg += "Word Count Stats:\n"
            msg += f"  Average: {avg_words:.1f}\n"
            msg += f"  Max: {max_words}\n\n"

        # Cloze statistics if any
        if cloze_counts:
            avg_cloze = sum(cloze_counts) / len(cloze_counts)
            max_cloze = max(cloze_counts)
            msg += f"Cloze Stats ({len(cloze_counts)} cloze cards):\n"
            msg += f"  Average deletions per card: {avg_cloze:.1f}\n"
            msg += f"  Max deletions in a card: {max_cloze}\n\n"

        # Card details if requested
        if include_card_details and card_details:
            msg += f"\nCard Details (first {min(10, len(card_details))}):\n"
            for detail in card_details[:10]:
                msg += f"  Note {detail['note_id']} [{detail['model']}]\n"
                msg += f"    Preview: {detail['preview']}\n"
                tags_str = ", ".join(detail["tags"]) if detail["tags"] else "(no tags)"  # type: ignore
                msg += f"    Tags: {tags_str}\n"

        msg += "\nThis is raw structural data. Use your judgment about quality "
        msg += "based on the specific learning context and goals."

        # Save raw data to database
        db = get_database()
        metadata = {
            "card_type_distribution": dict(type_counter),
            "tag_usage_percent": tag_usage / total_cards * 100 if total_cards > 0 else 0,
            "html_usage_percent": html_usage / total_cards * 100 if total_cards > 0 else 0,
            "avg_field_length": sum(field_lengths) / len(field_lengths) if field_lengths else 0,
        }
        db.save_deck_analysis(
            deck_name=deck_name,
            analysis_type="quality_raw",
            overall_score=None,
            total_cards=total_cards,
            metadata=metadata,
        )

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
async def analyze_deck_performance(
    deck_name: str,
    min_reviews: int = 1,
    lookback_days: int | None = None,
) -> CallToolResult:
    """Get performance data for a deck based on Anki metrics.

    Returns raw performance metrics (ease, lapses, intervals) from Anki.
    The LLM interprets this data based on learning context - no automatic scoring.

    Args:
        deck_name: Name of the deck to analyze
        min_reviews: Minimum reviews required to include card (default: 1)
        lookback_days: Historical window in days (None = all time, currently unused)

    Returns:
        Raw performance data for LLM analysis

    Examples:
        Basic performance analysis:
        >>> analyze_deck_performance("Biology::Cells")

        Only analyze reviewed cards:
        >>> analyze_deck_performance("Math", min_reviews=3)
    """
    try:
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

        # Fetch all cards in deck
        card_ids = await client.find_cards(f'deck:"{deck_name}"')

        if not card_ids:
            msg = f"Deck '{deck_name}' is empty (0 cards).\n\n"
            msg += "No performance data to analyze."
            return CallToolResult(content=[TextContent(type="text", text=msg)])

        # Get card details
        cards_info = await client.cards_info(card_ids)

        # Calculate metrics
        ease_values: list[float] = []
        lapses: list[int] = []
        intervals: list[int] = []
        new_count = 0
        learning_count = 0
        review_count = 0
        struggling_cards: list[dict[str, int | float]] = []

        for card in cards_info:
            # Card type: 0=new, 1=learning, 2=review, 3=relearning
            card_type = card.get("type", 0)
            if card_type == 0:
                new_count += 1
            elif card_type == 1:
                learning_count += 1
            else:
                review_count += 1

            # Get ease factor (Anki stores as integer, e.g., 2500 = 250%)
            ease = card.get("factor", 0) / 1000.0
            if ease > 0:
                ease_values.append(ease)

            # Get lapses and interval
            lapse_count = card.get("lapses", 0)
            lapses.append(lapse_count)

            interval_days = card.get("interval", 0)
            if interval_days > 0:
                intervals.append(interval_days)

            # Track struggling cards (low ease or high lapses)
            if ease > 0 and (ease < 1.5 or lapse_count > 2):
                struggling_cards.append(
                    {
                        "note_id": card.get("note", 0),
                        "ease": ease,
                        "lapses": lapse_count,
                        "interval": interval_days,
                    }
                )

        # Build response
        total_cards = len(cards_info)
        msg = f"Deck Performance Data: '{deck_name}'\n\n"

        # Card state distribution
        msg += "Card State Distribution:\n"
        msg += f"  New: {new_count} ({new_count / total_cards * 100:.0f}%)\n"
        msg += f"  Learning: {learning_count} ({learning_count / total_cards * 100:.0f}%)\n"
        msg += f"  Review: {review_count} ({review_count / total_cards * 100:.0f}%)\n\n"

        # Ease distribution
        if ease_values:
            avg_ease = sum(ease_values) / len(ease_values)
            min_ease = min(ease_values)
            max_ease = max(ease_values)

            # Bucket ease values
            ease_buckets = {"<1.5 (struggling)": 0, "1.5-2.0": 0, "2.0-2.5": 0, ">2.5": 0}
            for e in ease_values:
                if e < 1.5:
                    ease_buckets["<1.5 (struggling)"] += 1
                elif e < 2.0:
                    ease_buckets["1.5-2.0"] += 1
                elif e < 2.5:
                    ease_buckets["2.0-2.5"] += 1
                else:
                    ease_buckets[">2.5"] += 1

            msg += f"Ease Factor Stats ({len(ease_values)} cards with reviews):\n"
            msg += f"  Average: {avg_ease:.2f}\n"
            msg += f"  Min: {min_ease:.2f}\n"
            msg += f"  Max: {max_ease:.2f}\n"
            msg += "  Distribution:\n"
            for bucket, count in ease_buckets.items():
                pct = count / len(ease_values) * 100 if ease_values else 0
                msg += f"    {bucket}: {count} ({pct:.0f}%)\n"
            msg += "\n"

        # Lapse statistics
        if lapses:
            total_lapses = sum(lapses)
            cards_with_lapses = sum(1 for lapse in lapses if lapse > 0)
            max_lapses = max(lapses)
            msg += "Lapse Statistics:\n"
            msg += f"  Total lapses: {total_lapses}\n"
            msg += f"  Cards with lapses: {cards_with_lapses} "
            msg += f"({cards_with_lapses / total_cards * 100:.0f}%)\n"
            msg += f"  Max lapses on single card: {max_lapses}\n\n"

        # Interval statistics
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            max_interval = max(intervals)
            msg += "Interval Statistics (days):\n"
            msg += f"  Average: {avg_interval:.1f}\n"
            msg += f"  Max: {max_interval}\n\n"

        # Struggling cards
        if struggling_cards:
            msg += f"Potentially Struggling Cards ({len(struggling_cards)}):\n"
            # Sort by ease (lowest first)
            struggling_cards.sort(key=lambda x: x["ease"])
            for card in struggling_cards[:10]:
                msg += f"  Note {card['note_id']}: "
                msg += f"ease={card['ease']:.2f}, "
                msg += f"lapses={card['lapses']}, "
                msg += f"interval={card['interval']}d\n"
            if len(struggling_cards) > 10:
                msg += f"  ...and {len(struggling_cards) - 10} more\n"
            msg += "\n"

        msg += "This is raw performance data. Use your judgment about what needs "
        msg += "attention based on the specific learning context."

        # Save raw data to database
        db = get_database()
        metadata = {
            "new_count": new_count,
            "learning_count": learning_count,
            "review_count": review_count,
            "avg_ease": sum(ease_values) / len(ease_values) if ease_values else 0,
            "total_lapses": sum(lapses),
            "struggling_count": len(struggling_cards),
        }
        db.save_deck_analysis(
            deck_name=deck_name,
            analysis_type="performance_raw",
            overall_score=None,
            total_cards=total_cards,
            metadata=metadata,
        )

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
async def get_deck_recommendations(
    deck_name: str,
    max_recommendations: int = 10,
    focus_area: str = "both",
) -> CallToolResult:
    """Get prioritized recommendations for deck improvement.

    Synthesizes quality and performance analysis into actionable recommendations
    prioritized by impact/effort ratio. Provides quick wins and strategic improvements.

    Note: This tool provides structured suggestions based on patterns, but the LLM
    should use its judgment to prioritize based on the user's specific context.

    Args:
        deck_name: Name of the deck to analyze
        max_recommendations: Maximum recommendations to return (default: 10)
        focus_area: Analysis focus - "quality", "performance", or "both" (default: "both")

    Returns:
        Prioritized recommendations with impact, effort, and specific actions

    Examples:
        Comprehensive recommendations:
        >>> get_deck_recommendations("Biology::Cells")

        Focus on quality only:
        >>> get_deck_recommendations("Math", focus_area="quality")

        Limit to top 5:
        >>> get_deck_recommendations("Chemistry", max_recommendations=5)
    """
    # Note: This function is kept for backward compatibility but now returns
    # raw data that the LLM can interpret rather than prescriptive recommendations.
    try:
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

        # Validate focus_area
        if focus_area not in ["quality", "performance", "both"]:
            return CallToolResult(
                isError=True,
                content=[
                    TextContent(
                        type="text",
                        text=(
                            f"Invalid focus_area: '{focus_area}'. "
                            "Must be 'quality', 'performance', or 'both'."
                        ),
                    )
                ],
            )

        # Fetch card data
        card_ids = await client.find_cards(f'deck:"{deck_name}"')
        if not card_ids:
            msg = f"Deck '{deck_name}' is empty. No data to analyze for recommendations."
            return CallToolResult(content=[TextContent(type="text", text=msg)])

        cards_info = await client.cards_info(card_ids)
        note_ids = list({card["note"] for card in cards_info})
        notes_info = await client.notes_info(note_ids)

        # Collect observations (raw data, not judgments)
        observations: list[dict[str, str | int | float | list[int]]] = []

        # Quality observations
        if focus_area in ["quality", "both"]:
            # Tag usage
            tagged_count = sum(1 for n in notes_info if n.get("tags"))
            tag_pct = tagged_count / len(notes_info) * 100 if notes_info else 0
            tag_desc = f"{tagged_count} of {len(notes_info)} cards have tags ({tag_pct:.0f}%)"
            observations.append(
                {
                    "area": "quality",
                    "metric": "tag_usage",
                    "value": tag_pct,
                    "description": tag_desc,
                }
            )

            # Card type diversity
            type_counter: Counter[str] = Counter(n.get("modelName", "Unknown") for n in notes_info)
            if type_counter:
                dominant_type, dominant_count = type_counter.most_common(1)[0]
                dominant_pct = dominant_count / len(notes_info) * 100
                observations.append(
                    {
                        "area": "quality",
                        "metric": "type_diversity",
                        "value": dominant_pct,
                        "description": f"Most common type: {dominant_type} ({dominant_pct:.0f}%)",
                    }
                )

        # Performance observations
        if focus_area in ["performance", "both"]:
            # Struggling cards
            struggling: list[int] = []
            for card in cards_info:
                ease = card.get("factor", 0) / 1000.0
                lapse_count = card.get("lapses", 0)
                if ease > 0 and (ease < 1.5 or lapse_count > 2):
                    struggling.append(card.get("note", 0))

            observations.append(
                {
                    "area": "performance",
                    "metric": "struggling_cards",
                    "value": len(struggling),
                    "description": f"{len(struggling)} cards with ease <1.5 or lapses >2",
                    "note_ids": struggling[:20],
                }
            )

            # Average ease
            ease_values = [
                c.get("factor", 0) / 1000.0 for c in cards_info if c.get("factor", 0) > 0
            ]
            if ease_values:
                avg_ease = sum(ease_values) / len(ease_values)
                observations.append(
                    {
                        "area": "performance",
                        "metric": "avg_ease",
                        "value": avg_ease,
                        "description": f"Average ease factor: {avg_ease:.2f}",
                    }
                )

        # Format response
        msg = f"Deck Analysis Summary: '{deck_name}'\n"
        msg += f"Focus: {focus_area}\n\n"

        msg += "Observations (raw data for your interpretation):\n\n"

        for obs in observations:
            area = str(obs["area"]).upper()
            metric = obs["metric"]
            description = obs["description"]
            msg += f"  [{area}] {metric}\n"
            msg += f"    {description}\n"
            if "note_ids" in obs and obs["note_ids"]:
                note_ids_list = obs["note_ids"]
                if isinstance(note_ids_list, list):
                    msg += f"    Sample note IDs: {note_ids_list[:5]}\n"
            msg += "\n"

        msg += "Use your judgment to prioritize based on the user's learning goals. "
        msg += "Consider using inspect_card() to examine specific cards."

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
