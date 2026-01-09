"""Quality analysis for Anki decks."""

import random
from collections import Counter

from ..client import get_anki_client
from ..formatting import strip_html
from ..models import (
    BasicCard,
    ClozeCard,
    DeckPatterns,
    QualityReport,
    TypeInCard,
    ValidationSeverity,
)
from ..validators.card_validator import get_validator


class DeckQualityAnalyzer:
    """Analyzes deck quality against spaced repetition best practices."""

    def __init__(self):
        """Initialize quality analyzer."""
        self.client = get_anki_client()
        self.validator = get_validator()

    async def analyze(self, deck_name: str, sample_size: int | None = None) -> QualityReport:
        """Analyze deck quality.

        Args:
            deck_name: Name of deck to analyze
            sample_size: Optional sample size (None = analyze all cards)

        Returns:
            QualityReport with scores, issues, and patterns
        """
        # Fetch all cards in deck
        card_ids = await self.client.find_cards(f'deck:"{deck_name}"')

        if not card_ids:
            # Return empty report for empty deck
            return QualityReport(
                score=100.0,
                total_cards=0,
                issues_by_severity={"error": 0, "warning": 0, "suggestion": 0},
                top_issues=[],
                deck_patterns=DeckPatterns(
                    tag_consistency=0.0,
                    type_distribution={},
                    html_usage_percent=0.0,
                    avg_field_length=0.0,
                ),
                problematic_card_ids=[],
            )

        # Sample if requested
        if sample_size and sample_size < len(card_ids):
            card_ids = random.sample(card_ids, sample_size)

        # Get note details
        cards_info = await self.client.cards_info(card_ids)
        note_ids = list({card["note"] for card in cards_info})
        notes_info = await self.client.notes_info(note_ids)

        # Validate each card
        validation_results = []
        problematic_card_ids = []

        for note in notes_info:
            card_obj = self._convert_note_to_card(note)
            if card_obj:
                results = self.validator.validate(card_obj)
                validation_results.append((note["noteId"], results))

                # Track problematic cards (any errors or warnings)
                if any(
                    r.severity in [ValidationSeverity.ERROR, ValidationSeverity.WARNING]
                    for r in results
                ):
                    problematic_card_ids.append(note["noteId"])

        # Analyze deck-level patterns
        deck_patterns = self._analyze_deck_patterns(notes_info)

        # Calculate quality score
        score = self._calculate_quality_score(validation_results, deck_patterns)

        # Get issue breakdown by severity
        issues_by_severity = self._group_by_severity(validation_results)

        # Get top 5 issues
        top_issues = self._get_top_issues(validation_results)

        return QualityReport(
            score=score,
            total_cards=len(notes_info),
            issues_by_severity=issues_by_severity,
            top_issues=top_issues,
            deck_patterns=deck_patterns,
            problematic_card_ids=problematic_card_ids,
        )

    def _convert_note_to_card(self, note: dict) -> BasicCard | ClozeCard | TypeInCard | None:
        """Convert Anki note to card model for validation.

        Args:
            note: Note info dict from AnkiConnect

        Returns:
            Card model or None if conversion fails
        """
        model_name = note.get("modelName", "")
        fields = note.get("fields", {})
        tags = note.get("tags", [])

        try:
            if model_name == "Cloze":
                text = fields.get("Text", {}).get("value", "")
                extra = fields.get("Extra", {}).get("value")
                return ClozeCard(text=text, tags=tags, extra=extra)

            elif model_name == "Basic (type in the answer)":
                front = fields.get("Front", {}).get("value", "")
                back = fields.get("Back", {}).get("value", "")
                return TypeInCard(front=front, back=back, tags=tags)

            elif model_name == "Basic":
                front = fields.get("Front", {}).get("value", "")
                back = fields.get("Back", {}).get("value", "")
                return BasicCard(front=front, back=back, tags=tags)

            else:
                # Generic handling for other note types
                # Try to extract first two fields as front/back
                field_values = [f.get("value", "") for f in fields.values()]
                if len(field_values) >= 2:
                    return BasicCard(front=field_values[0], back=field_values[1], tags=tags)

        except Exception:
            # If conversion fails, skip this card
            pass

        return None

    def _analyze_deck_patterns(self, notes_info: list[dict]) -> DeckPatterns:
        """Analyze deck-level patterns.

        Args:
            notes_info: List of note info dicts

        Returns:
            DeckPatterns with consistency metrics
        """
        if not notes_info:
            return DeckPatterns(
                tag_consistency=0.0,
                type_distribution={},
                html_usage_percent=0.0,
                avg_field_length=0.0,
            )

        # Tag consistency: What % of cards are tagged?
        tagged_count = sum(1 for n in notes_info if n.get("tags"))
        tag_consistency = tagged_count / len(notes_info)

        # Type distribution
        type_counter = Counter(n.get("modelName", "Unknown") for n in notes_info)
        type_distribution = {k: round(v / len(notes_info), 2) for k, v in type_counter.items()}

        # HTML usage detection
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
        html_usage_count = 0
        field_lengths = []

        for note in notes_info:
            fields = note.get("fields", {})
            note_has_html = False

            for field_data in fields.values():
                field_value = field_data.get("value", "")

                # Check for HTML
                if any(tag in field_value for tag in html_tags):
                    note_has_html = True

                # Track field length (without HTML)
                clean_text = strip_html(field_value)
                field_lengths.append(len(clean_text))

            if note_has_html:
                html_usage_count += 1

        html_usage_percent = (
            round(html_usage_count / len(notes_info) * 100, 1) if notes_info else 0.0
        )
        avg_field_length = (
            round(sum(field_lengths) / len(field_lengths), 1) if field_lengths else 0.0
        )

        return DeckPatterns(
            tag_consistency=round(tag_consistency, 2),
            type_distribution=type_distribution,
            html_usage_percent=html_usage_percent,
            avg_field_length=avg_field_length,
        )

    def _calculate_quality_score(
        self, validation_results: list[tuple[int, list]], deck_patterns: DeckPatterns
    ) -> float:
        """Calculate overall quality score.

        Args:
            validation_results: List of (note_id, validation_results) tuples
            deck_patterns: Deck-level pattern analysis

        Returns:
            Quality score from 0-100
        """
        # Count issues by severity
        error_count = 0
        warning_count = 0
        suggestion_count = 0

        for _, results in validation_results:
            for result in results:
                if result.severity == ValidationSeverity.ERROR:
                    error_count += 1
                elif result.severity == ValidationSeverity.WARNING:
                    warning_count += 1
                elif result.severity == ValidationSeverity.SUGGESTION:
                    suggestion_count += 1

        # Base score: 100 - penalties
        score = 100.0

        # Penalty for errors (10 points each, capped at 50)
        score -= min(error_count * 10, 50)

        # Penalty for warnings (3 points each, capped at 30)
        score -= min(warning_count * 3, 30)

        # Penalty for suggestions (1 point each, capped at 15)
        score -= min(suggestion_count * 1, 15)

        # Deck-level penalties
        # Low tag consistency (up to 5 points)
        if deck_patterns.tag_consistency < 0.5:
            score -= (0.5 - deck_patterns.tag_consistency) * 10

        # Ensure score is in valid range
        return max(0.0, min(100.0, round(score, 1)))

    def _group_by_severity(self, validation_results: list[tuple[int, list]]) -> dict[str, int]:
        """Group issues by severity.

        Args:
            validation_results: List of (note_id, validation_results) tuples

        Returns:
            Dictionary with counts by severity level
        """
        counts = {"error": 0, "warning": 0, "suggestion": 0}

        for _, results in validation_results:
            for result in results:
                counts[result.severity.value] += 1

        return counts

    def _get_top_issues(self, validation_results: list[tuple[int, list]]) -> list[tuple[str, int]]:
        """Get top 5 most common issues.

        Args:
            validation_results: List of (note_id, validation_results) tuples

        Returns:
            List of (issue_type, count) tuples sorted by frequency
        """
        issue_counter: Counter[str] = Counter()

        for _, results in validation_results:
            for result in results:
                # Use the rule name as issue type
                issue_counter[result.rule] += 1

        # Return top 5
        return issue_counter.most_common(5)

    def format_report(
        self, report: QualityReport, deck_name: str, sample_size: int | None = None
    ) -> str:
        """Format quality report as human-readable text.

        Args:
            report: Quality report to format
            deck_name: Name of the analyzed deck
            sample_size: Optional sample size used

        Returns:
            Formatted report text
        """
        sample_text = (
            f" (analyzed sample of {report.total_cards})"
            if sample_size and sample_size < report.total_cards
            else ""
        )
        msg = f'Deck Quality Analysis: "{deck_name}"{sample_text}\n\n'

        # Overall score with interpretation
        msg += f"Overall Score: {report.score:.1f}/100 "
        if report.score >= 80:
            msg += "(Excellent)\n"
        elif report.score >= 60:
            msg += "(Good)\n"
        elif report.score >= 40:
            msg += "(Needs Improvement)\n"
        else:
            msg += "(Poor)\n"

        msg += f"Total Cards: {report.total_cards}\n\n"

        # Issue breakdown
        msg += "Issue Breakdown:\n"
        msg += f"  Errors: {report.issues_by_severity['error']}\n"
        msg += f"  Warnings: {report.issues_by_severity['warning']}\n"
        msg += f"  Suggestions: {report.issues_by_severity['suggestion']}\n\n"

        # Top issues
        if report.top_issues:
            msg += "Top Issues:\n"
            for idx, (rule, count) in enumerate(report.top_issues, 1):
                # Convert rule name to readable format
                readable_rule = rule.replace("_", " ").title()
                msg += f"{idx}. {readable_rule}: {count} cards\n"
            msg += "\n"

        # Deck patterns
        patterns = report.deck_patterns
        msg += "Deck Patterns:\n"
        msg += f"  Tag Consistency: {patterns.tag_consistency:.0%} "
        if patterns.tag_consistency < 0.3:
            msg += "(Low - consider adding tags)\n"
        elif patterns.tag_consistency < 0.7:
            msg += "(Moderate)\n"
        else:
            msg += "(Good)\n"

        msg += f"  HTML Usage: {patterns.html_usage_percent:.0f}% of cards\n"
        msg += f"  Avg Field Length: {patterns.avg_field_length:.0f} characters\n\n"

        # Card type distribution
        msg += "Card Type Distribution:\n"
        for card_type, ratio in patterns.type_distribution.items():
            msg += f"  {card_type}: {ratio:.0%}\n"

        # Check for type imbalance
        if patterns.type_distribution:
            max_ratio = max(patterns.type_distribution.values())
            if max_ratio > 0.8:
                msg += "\n⚠ Deck heavily uses one card type - consider diversifying\n"

        # Next steps
        msg += "\nNext Steps:\n"
        if report.score < 60:
            msg += "- Use get_deck_recommendations for prioritized improvement plan\n"
        msg += "- Use inspect_card(note_id) to review specific problematic cards\n"
        msg += "- Use analyze_deck_performance to correlate with study metrics\n"

        return msg.strip()
