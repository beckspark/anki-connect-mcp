"""Recommendation engine for deck improvements."""

from ..models import PerformanceReport, QualityReport, Recommendation


class RecommendationEngine:
    """Generates prioritized recommendations for deck improvement."""

    # Impact scoring constants
    IMPACT_HIGH = 10
    IMPACT_MEDIUM = 5
    IMPACT_LOW = 2

    # Effort scoring constants
    EFFORT_QUICK = 1  # <5 min
    EFFORT_MODERATE = 3  # <30 min
    EFFORT_LARGE = 10  # >1 hour

    def generate(
        self,
        quality_report: QualityReport | None,
        performance_report: PerformanceReport | None,
        max_recommendations: int = 10,
    ) -> list[Recommendation]:
        """Generate prioritized recommendations.

        Args:
            quality_report: Optional quality analysis report
            performance_report: Optional performance analysis report
            max_recommendations: Maximum recommendations to return (default: 10)

        Returns:
            List of recommendations sorted by priority score (highest first)
        """
        recommendations = []

        # Generate quality-based recommendations
        if quality_report:
            recommendations.extend(self._quality_recommendations(quality_report))

        # Generate performance-based recommendations
        if performance_report:
            recommendations.extend(self._performance_recommendations(performance_report))

        # Generate combined recommendations (quality + performance correlation)
        if quality_report and performance_report:
            recommendations.extend(
                self._combined_recommendations(quality_report, performance_report)
            )

        # Calculate priority scores
        for rec in recommendations:
            rec.priority_score = self._calculate_priority(rec)

        # Sort by priority (highest first) and limit
        recommendations.sort(key=lambda r: r.priority_score, reverse=True)
        return recommendations[:max_recommendations]

    def _quality_recommendations(self, report: QualityReport) -> list[Recommendation]:
        """Generate recommendations from quality analysis."""
        recs = []

        # Recommendation 1: Fix cards with validation errors
        error_count = report.issues_by_severity.get("error", 0)
        if error_count > 0:
            recs.append(
                Recommendation(
                    title=f"Fix {error_count} cards with validation errors",
                    impact="high",
                    effort="quick" if error_count <= 5 else "moderate",
                    priority_score=0.0,  # Will be calculated
                    description=(
                        "These cards have critical validation errors that prevent "
                        "effective learning (e.g., malformed cloze deletions)."
                    ),
                    affected_card_ids=report.problematic_card_ids[:error_count],
                )
            )

        # Recommendation 2: Address warning-level issues
        warning_count = report.issues_by_severity.get("warning", 0)
        if warning_count > 5:
            # Find most common warning type
            top_warning = None
            for rule, count in report.top_issues:
                if count > 0:
                    top_warning = (rule, count)
                    break

            if top_warning:
                rule_name, count = top_warning
                readable_rule = rule_name.replace("_", " ").lower()
                recs.append(
                    Recommendation(
                        title=f"Address {count} cards with {readable_rule}",
                        impact="high",
                        effort="moderate" if count > 10 else "quick",
                        priority_score=0.0,
                        description=(
                            f"Most common issue: {readable_rule}. "
                            "These reduce retention efficiency."
                        ),
                        affected_card_ids=report.problematic_card_ids[:count],
                    )
                )

        # Recommendation 3: Improve tag consistency
        if report.deck_patterns.tag_consistency < 0.5:
            untagged_estimate = int(
                report.total_cards * (1 - report.deck_patterns.tag_consistency)
            )
            recs.append(
                Recommendation(
                    title=f"Add tags to {untagged_estimate} untagged cards",
                    impact="medium",
                    effort="quick" if untagged_estimate < 20 else "moderate",
                    priority_score=0.0,
                    description=(
                        f"Only {report.deck_patterns.tag_consistency:.0%} of cards have tags. "
                        "Tags improve organization and selective studying."
                    ),
                )
            )

        # Recommendation 4: Balance card type distribution
        if report.deck_patterns.type_distribution:
            max_type_ratio = max(report.deck_patterns.type_distribution.values())
            if max_type_ratio > 0.8:
                dominant_type = max(
                    report.deck_patterns.type_distribution.items(), key=lambda x: x[1]
                )[0]
                recs.append(
                    Recommendation(
                        title=f"Diversify card types (currently {max_type_ratio:.0%} {dominant_type})",
                        impact="medium",
                        effort="moderate",
                        priority_score=0.0,
                        description=(
                            f"Deck is heavily {dominant_type} cards. Consider converting some "
                            "to other formats for variety and better retention."
                        ),
                    )
                )

        return recs

    def _performance_recommendations(self, report: PerformanceReport) -> list[Recommendation]:
        """Generate recommendations from performance analysis."""
        recs = []

        # Recommendation 1: Address struggling cards
        if report.struggling_cards:
            count = len(report.struggling_cards)
            recs.append(
                Recommendation(
                    title=f"Review and fix {count} struggling cards",
                    impact="high",
                    effort="quick" if count <= 5 else "moderate",
                    priority_score=0.0,
                    description=(
                        f"These {count} cards have ease <1.5 or lapses >2. "
                        "They likely need clarification, splitting, or simplification."
                    ),
                    affected_card_ids=[card.note_id for card in report.struggling_cards],
                )
            )

        # Recommendation 2: Improve low retention rate
        if report.retention_rate < 0.75:
            recs.append(
                Recommendation(
                    title=f"Improve retention rate (currently {report.retention_rate:.0%})",
                    impact="high",
                    effort="moderate",
                    priority_score=0.0,
                    description=(
                        "Retention below 75% indicates cards may be too difficult. "
                        "Consider reducing new cards per day and reviewing struggling cards."
                    ),
                )
            )

        # Recommendation 3: Address high lapse rate
        if report.lapse_rate > 0.25:
            recs.append(
                Recommendation(
                    title=f"Reduce lapse rate (currently {report.lapse_rate:.0%})",
                    impact="medium",
                    effort="moderate",
                    priority_score=0.0,
                    description=(
                        "High lapse rate suggests cards are being forgotten frequently. "
                        "Review card clarity and consider splitting complex cards."
                    ),
                )
            )

        return recs

    def _combined_recommendations(
        self, quality_report: QualityReport, performance_report: PerformanceReport
    ) -> list[Recommendation]:
        """Generate recommendations by correlating quality and performance."""
        recs = []

        # Find struggling cards that also have quality issues
        struggling_note_ids = {card.note_id for card in performance_report.struggling_cards}
        struggling_with_issues = [
            nid for nid in quality_report.problematic_card_ids if nid in struggling_note_ids
        ]

        if struggling_with_issues:
            recs.append(
                Recommendation(
                    title=f"Fix {len(struggling_with_issues)} cards with both quality and performance issues",
                    impact="high",
                    effort="quick",
                    priority_score=0.0,
                    description=(
                        "These cards have low performance AND quality issues. "
                        "Clear wins: fixing quality will likely improve retention."
                    ),
                    affected_card_ids=struggling_with_issues[:10],
                    example_before_after=(
                        "Example: Split 'Describe mitochondria structure AND function' → "
                        "Card 1: 'What is the structure of mitochondria?' + "
                        "Card 2: 'What is the function of mitochondria?'"
                    ),
                )
            )

        # If low retention correlates with high warning count
        if performance_report.retention_rate < 0.8 and quality_report.issues_by_severity.get(
            "warning", 0
        ) > 10:
            recs.append(
                Recommendation(
                    title="Address quality warnings to improve retention",
                    impact="high",
                    effort="moderate",
                    priority_score=0.0,
                    description=(
                        f"Retention at {performance_report.retention_rate:.0%} with "
                        f"{quality_report.issues_by_severity['warning']} quality warnings. "
                        "Fixing card quality issues will likely improve retention."
                    ),
                )
            )

        return recs

    def _calculate_priority(self, rec: Recommendation) -> float:
        """Calculate priority score using Impact/Effort matrix.

        Priority = Impact / Effort (bang for buck)

        Args:
            rec: Recommendation to score

        Returns:
            Priority score (higher is better)
        """
        impact_values = {
            "high": self.IMPACT_HIGH,
            "medium": self.IMPACT_MEDIUM,
            "low": self.IMPACT_LOW,
        }
        effort_values = {
            "quick": self.EFFORT_QUICK,
            "moderate": self.EFFORT_MODERATE,
            "large": self.EFFORT_LARGE,
        }

        impact = impact_values.get(rec.impact, self.IMPACT_MEDIUM)
        effort = effort_values.get(rec.effort, self.EFFORT_MODERATE)

        return round(impact / effort, 2)

    def format_recommendations(
        self, recommendations: list[Recommendation], deck_name: str
    ) -> str:
        """Format recommendations as human-readable text.

        Args:
            recommendations: List of recommendations to format
            deck_name: Name of the analyzed deck

        Returns:
            Formatted recommendations text
        """
        if not recommendations:
            msg = f'Deck Recommendations: "{deck_name}"\n\n'
            msg += "No recommendations - deck is in good shape!\n\n"
            msg += "Continue studying and run periodic analyses to maintain quality."
            return msg

        msg = f'Deck Recommendations: "{deck_name}"\n'
        msg += f"Generated {len(recommendations)} prioritized recommendations\n\n"

        # Group by priority tiers
        quick_wins = [r for r in recommendations if r.priority_score >= 5.0]
        schedule_soon = [
            r for r in recommendations if 2.0 <= r.priority_score < 5.0
        ]
        consider = [r for r in recommendations if r.priority_score < 2.0]

        if quick_wins:
            msg += "=== QUICK WINS (High Impact, Low Effort) ===\n\n"
            for idx, rec in enumerate(quick_wins, 1):
                msg += self._format_recommendation(idx, rec)

        if schedule_soon:
            msg += "\n=== SCHEDULE SOON (Good Impact/Effort Ratio) ===\n\n"
            for idx, rec in enumerate(schedule_soon, len(quick_wins) + 1):
                msg += self._format_recommendation(idx, rec)

        if consider:
            msg += "\n=== CONSIDER (Lower Priority) ===\n\n"
            for idx, rec in enumerate(consider, len(quick_wins) + len(schedule_soon) + 1):
                msg += self._format_recommendation(idx, rec)

        # Add tracking note
        msg += "\n=== TRACK PROGRESS ===\n"
        msg += "Run this analysis monthly to track improvements.\n"
        msg += "Use inspect_card(note_id) to examine specific cards.\n"

        return msg.strip()

    def _format_recommendation(self, idx: int, rec: Recommendation) -> str:
        """Format a single recommendation."""
        msg = f"{idx}. {rec.title} [Priority: {rec.priority_score:.1f}]\n"
        msg += f"   Impact: {rec.impact.title()} | Effort: {rec.effort.title()}\n"
        msg += f"   {rec.description}\n"

        if rec.affected_card_ids:
            msg += f"   Affected cards: {len(rec.affected_card_ids)}\n"

        if rec.example_before_after:
            msg += f"   {rec.example_before_after}\n"

        msg += "\n"
        return msg
