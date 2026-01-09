"""MCP tools for deck analysis and recommendations."""

from mcp.types import CallToolResult, TextContent

from ..analyzers.performance import DeckPerformanceAnalyzer
from ..analyzers.quality import DeckQualityAnalyzer
from ..analyzers.recommendations import RecommendationEngine
from ..client import AnkiConnectionError, get_anki_client
from ..db.database import get_database
from ..server import app


@app.tool()
async def analyze_deck_quality(
    deck_name: str,
    sample_size: int | None = None,
    include_card_details: bool = False,
) -> CallToolResult:
    """Analyze deck quality against spaced repetition best practices.

    Fast structural analysis that validates all cards against established rules
    and detects deck-level patterns. No review history needed.

    Args:
        deck_name: Name of the deck to analyze
        sample_size: Optional sample size (None = analyze all cards)
        include_card_details: Include list of problematic card IDs (default: False)

    Returns:
        Quality analysis report with score, issues, and patterns

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

        # Analyze deck
        analyzer = DeckQualityAnalyzer()
        report = await analyzer.analyze(deck_name, sample_size)

        # Save to database
        db = get_database()
        metadata = {
            "issues_by_severity": report.issues_by_severity,
            "top_issues": [{"rule": rule, "count": count} for rule, count in report.top_issues],
            "deck_patterns": report.deck_patterns.model_dump(),
        }
        db.save_deck_analysis(
            deck_name=deck_name,
            analysis_type="quality",
            overall_score=report.score,
            total_cards=report.total_cards,
            metadata=metadata,
        )

        # Format report
        msg = analyzer.format_report(report, deck_name, sample_size)

        # Optional: Include problematic card details
        if include_card_details and report.problematic_card_ids:
            msg += f"\n\nProblematic Cards ({len(report.problematic_card_ids)}):\n"
            for note_id in report.problematic_card_ids[:10]:
                msg += f"  Note ID: {note_id}\n"
            if len(report.problematic_card_ids) > 10:
                remaining = len(report.problematic_card_ids) - 10
                msg += f"  ...and {remaining} more\n"

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
    """Analyze deck performance based on review metrics.

    Analyzes Anki performance metrics including retention rate, ease distribution,
    lapse rate, and identifies struggling cards. Uses card metadata (ease, lapses,
    intervals) to provide insights into which cards need attention.

    Args:
        deck_name: Name of the deck to analyze
        min_reviews: Minimum reviews required to include card (default: 1)
        lookback_days: Historical window in days (None = all time, currently unused in MVP)

    Returns:
        Performance analysis report with metrics and struggling cards

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

        # Analyze deck
        analyzer = DeckPerformanceAnalyzer()
        report = await analyzer.analyze(deck_name, min_reviews, lookback_days)

        # Save to database
        db = get_database()
        metadata = {
            "retention_rate": report.retention_rate,
            "ease_distribution": report.ease_distribution,
            "lapse_rate": report.lapse_rate,
            "maturity_breakdown": report.maturity_breakdown,
            "struggling_count": len(report.struggling_cards),
        }
        db.save_deck_analysis(
            deck_name=deck_name,
            analysis_type="performance",
            overall_score=report.retention_rate,
            total_cards=sum(report.maturity_breakdown.values()),
            metadata=metadata,
        )

        # Format report
        msg = analyzer.format_report(report, deck_name)

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

        # Run analyses based on focus area
        quality_report = None
        performance_report = None

        if focus_area in ["quality", "both"]:
            quality_analyzer = DeckQualityAnalyzer()
            quality_report = await quality_analyzer.analyze(deck_name)

        if focus_area in ["performance", "both"]:
            performance_analyzer = DeckPerformanceAnalyzer()
            performance_report = await performance_analyzer.analyze(deck_name)

        # Generate recommendations
        engine = RecommendationEngine()
        recommendations = engine.generate(quality_report, performance_report, max_recommendations)

        # Save to database (store top recommendation titles as metadata)
        db = get_database()
        metadata = {
            "focus_area": focus_area,
            "recommendation_count": len(recommendations),
            "top_recommendations": [
                {"title": rec.title, "priority": rec.priority_score} for rec in recommendations[:5]
            ],
        }
        db.save_deck_analysis(
            deck_name=deck_name,
            analysis_type="recommendations",
            overall_score=None,
            total_cards=quality_report.total_cards if quality_report else 0,
            metadata=metadata,
        )

        # Format recommendations
        msg = engine.format_recommendations(recommendations, deck_name)

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
