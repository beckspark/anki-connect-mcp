"""Performance analysis for Anki decks."""

from ..client import get_anki_client
from ..models import PerformanceReport, StrugglingCard


class DeckPerformanceAnalyzer:
    """Analyzes deck performance based on review history and card metrics."""

    def __init__(self):
        """Initialize performance analyzer."""
        self.client = get_anki_client()

    async def analyze(
        self,
        deck_name: str,
        min_reviews: int = 1,
        lookback_days: int | None = None,
    ) -> PerformanceReport:
        """Analyze deck performance metrics.

        Args:
            deck_name: Name of deck to analyze
            min_reviews: Minimum reviews required to include card (default: 1)
            lookback_days: Historical window in days (None = all time)

        Returns:
            PerformanceReport with retention, ease, and struggling cards
        """
        # Fetch all cards in deck
        card_ids = await self.client.find_cards(f'deck:"{deck_name}"')

        if not card_ids:
            # Return empty report for empty deck
            return PerformanceReport(
                retention_rate=0.0,
                ease_distribution={},
                lapse_rate=0.0,
                struggling_cards=[],
                maturity_breakdown={},
                total_reviews=0,
            )

        # Get card details
        cards_info = await self.client.cards_info(card_ids)

        # Filter cards by review count
        reviewed_cards = [card for card in cards_info if card.get("reps", 0) >= min_reviews]

        if not reviewed_cards:
            return PerformanceReport(
                retention_rate=0.0,
                ease_distribution={},
                lapse_rate=0.0,
                struggling_cards=[],
                maturity_breakdown={"young": 0, "mature": 0, "very_mature": 0},
                total_reviews=0,
            )

        # Calculate metrics from card metadata
        retention_rate = self._calculate_retention(reviewed_cards)
        ease_distribution = self._calculate_ease_distribution(reviewed_cards)
        lapse_rate = self._calculate_lapse_rate(reviewed_cards)
        struggling_cards = self._identify_struggling_cards(reviewed_cards)
        maturity_breakdown = self._calculate_maturity(reviewed_cards)

        # Count total reviews
        total_reviews = sum(card.get("reps", 0) for card in reviewed_cards)

        return PerformanceReport(
            retention_rate=retention_rate,
            ease_distribution=ease_distribution,
            lapse_rate=lapse_rate,
            struggling_cards=struggling_cards,
            maturity_breakdown=maturity_breakdown,
            total_reviews=total_reviews,
        )

    def _calculate_retention(self, cards: list[dict]) -> float:
        """Calculate retention rate from card success metrics.

        Anki doesn't directly provide "retention rate", but we can estimate it
        using the ratio of (reviews - lapses) / reviews.

        Args:
            cards: List of card info dicts

        Returns:
            Estimated retention rate (0.0-1.0)
        """
        total_reviews = 0
        total_lapses = 0

        for card in cards:
            reps = card.get("reps", 0)
            lapses = card.get("lapses", 0)
            total_reviews += reps
            total_lapses += lapses

        if total_reviews == 0:
            return 0.0

        # Retention = (reviews - lapses) / reviews
        return max(0.0, min(1.0, (total_reviews - total_lapses) / total_reviews))

    def _calculate_ease_distribution(self, cards: list[dict]) -> dict[str, int]:
        """Calculate distribution of cards by ease factor.

        Args:
            cards: List of card info dicts

        Returns:
            Dictionary with counts for each ease bucket
        """
        distribution = {
            "<1.5": 0,  # Struggling
            "1.5-2.0": 0,  # Difficult
            "2.0-2.5": 0,  # Normal
            "2.5-3.0": 0,  # Easy
            ">3.0": 0,  # Very Easy
        }

        for card in cards:
            # Anki stores ease as factor * 1000 (e.g., 2500 = 2.5x)
            ease_factor = card.get("factor", 2500) / 1000.0

            if ease_factor < 1.5:
                distribution["<1.5"] += 1
            elif ease_factor < 2.0:
                distribution["1.5-2.0"] += 1
            elif ease_factor < 2.5:
                distribution["2.0-2.5"] += 1
            elif ease_factor < 3.0:
                distribution["2.5-3.0"] += 1
            else:
                distribution[">3.0"] += 1

        return distribution

    def _calculate_lapse_rate(self, cards: list[dict]) -> float:
        """Calculate percentage of cards with lapses.

        Args:
            cards: List of card info dicts

        Returns:
            Lapse rate (0.0-1.0)
        """
        if not cards:
            return 0.0

        cards_with_lapses = sum(1 for card in cards if card.get("lapses", 0) > 0)
        return cards_with_lapses / len(cards)

    def _identify_struggling_cards(self, cards: list[dict]) -> list[StrugglingCard]:
        """Identify cards with performance issues.

        A card is considered struggling if:
        - Ease factor < 1.5 (low ease)
        - OR Lapses > 2 (frequently forgotten)

        Args:
            cards: List of card info dicts

        Returns:
            List of struggling cards sorted by ease (lowest first)
        """
        struggling = []

        for card in cards:
            ease = card.get("factor", 2500) / 1000.0
            lapses = card.get("lapses", 0)
            interval = card.get("interval", 0)

            if ease < 1.5 or lapses > 2:
                struggling.append(
                    StrugglingCard(
                        note_id=card["note"],
                        ease=round(ease, 2),
                        lapses=lapses,
                        interval_days=interval,
                    )
                )

        # Sort by ease (lowest first), then by lapses (highest first)
        struggling.sort(key=lambda x: (x.ease, -x.lapses))

        return struggling

    def _calculate_maturity(self, cards: list[dict]) -> dict[str, int]:
        """Calculate distribution by card maturity.

        Maturity is based on interval:
        - Young: < 21 days
        - Mature: 21-90 days
        - Very Mature: > 90 days

        Args:
            cards: List of card info dicts

        Returns:
            Dictionary with counts for each maturity level
        """
        breakdown = {"young": 0, "mature": 0, "very_mature": 0}

        for card in cards:
            interval = card.get("interval", 0)

            if interval < 21:
                breakdown["young"] += 1
            elif interval < 90:
                breakdown["mature"] += 1
            else:
                breakdown["very_mature"] += 1

        return breakdown

    def format_report(self, report: PerformanceReport, deck_name: str) -> str:
        """Format performance report as human-readable text.

        Args:
            report: Performance report to format
            deck_name: Name of the analyzed deck

        Returns:
            Formatted report text
        """
        total_cards = sum(report.maturity_breakdown.values())
        msg = f'Deck Performance Analysis: "{deck_name}"\n\n'

        if total_cards == 0:
            msg += "No reviewed cards found in this deck.\n"
            msg += "Study some cards first, then run this analysis again."
            return msg

        # Retention rate
        retention_pct = report.retention_rate * 100
        msg += f"Retention Rate: {retention_pct:.1f}% "
        if retention_pct >= 85:
            msg += "(Excellent - target: 85-90%)\n"
        elif retention_pct >= 75:
            msg += "(Good - target: 85-90%)\n"
        elif retention_pct >= 65:
            msg += "(Fair - consider reviewing struggling cards)\n"
        else:
            msg += "(Low - cards may be too difficult)\n"

        msg += f"Total Reviews: {report.total_reviews:,}\n"
        msg += f"Cards Analyzed: {total_cards}\n\n"

        # Ease distribution
        msg += "Ease Distribution:\n"
        ease_labels = {
            "<1.5": "Struggling",
            "1.5-2.0": "Difficult",
            "2.0-2.5": "Normal",
            "2.5-3.0": "Easy",
            ">3.0": "Very Easy",
        }

        for bucket, count in report.ease_distribution.items():
            if total_cards > 0:
                pct = (count / total_cards) * 100
                label = ease_labels.get(bucket, bucket)
                msg += f"  {bucket} ({label}): {count} ({pct:.0f}%)\n"

        # Lapse rate
        msg += f"\nLapse Rate: {report.lapse_rate*100:.1f}% "
        if report.lapse_rate > 0.3:
            msg += "(High - many cards being forgotten)\n"
        elif report.lapse_rate > 0.15:
            msg += "(Moderate)\n"
        else:
            msg += "(Low - good retention)\n"

        # Struggling cards
        if report.struggling_cards:
            msg += f"\nStruggling Cards ({len(report.struggling_cards)}):\n"
            msg += "Cards with ease <1.5 OR lapses >2:\n\n"

            for idx, card in enumerate(report.struggling_cards[:10], 1):
                msg += f"{idx}. Note ID {card.note_id}\n"
                msg += f"   Ease: {card.ease:.2f}, Lapses: {card.lapses}, "
                msg += f"Interval: {card.interval_days} days\n"

            if len(report.struggling_cards) > 10:
                remaining = len(report.struggling_cards) - 10
                msg += f"\n...and {remaining} more struggling cards\n"

        # Maturity breakdown
        msg += "\nMaturity Breakdown:\n"
        maturity_labels = {
            "young": "Young (<21 days)",
            "mature": "Mature (21-90 days)",
            "very_mature": "Very Mature (>90 days)",
        }

        for level, count in report.maturity_breakdown.items():
            if total_cards > 0:
                pct = (count / total_cards) * 100
                label = maturity_labels.get(level, level)
                msg += f"  {label}: {count} ({pct:.0f}%)\n"

        # Recommendations
        msg += "\nNext Steps:\n"
        if report.struggling_cards:
            msg += f"- Review {len(report.struggling_cards)} struggling cards\n"
            msg += "- Use inspect_card(note_id) to examine specific cards\n"
            msg += "- Use get_deck_recommendations for prioritized fixes\n"
        if retention_pct < 75:
            msg += "- Consider reducing new cards per day\n"
            msg += "- Check if cards are too ambiguous or complex\n"
        msg += "- Use analyze_deck_quality to check for card quality issues\n"

        return msg.strip()
