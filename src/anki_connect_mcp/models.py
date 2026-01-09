"""Pydantic models for cards, validation results, and data structures."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class CardType(str, Enum):
    """Supported Anki card types."""

    BASIC = "basic"
    CLOZE = "cloze"
    TYPE_IN = "type_in"


class ValidationSeverity(str, Enum):
    """Validation result severity levels."""

    ERROR = "error"  # Blocks card creation
    WARNING = "warning"  # Shows warning but allows creation
    SUGGESTION = "suggestion"  # Best practice tip


class ValidationResult(BaseModel):
    """Result from a single validation rule."""

    severity: ValidationSeverity
    rule: str = Field(description="Name of the validation rule")
    message: str = Field(description="Human-readable validation message")
    field: str | None = Field(default=None, description="Field that failed validation")


class BasicCard(BaseModel):
    """Basic flashcard with front and back."""

    front: str = Field(min_length=1, max_length=1000, description="Question or prompt")
    back: str = Field(min_length=1, max_length=2000, description="Answer")
    tags: list[str] = Field(default_factory=list, description="Tags for the card")
    deck: str | None = Field(default=None, description="Deck name (uses default if not provided)")

    @field_validator("front", "back")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip()


class ClozeCard(BaseModel):
    """Cloze deletion card."""

    text: str = Field(min_length=1, description="Text with cloze deletions in {{c1::text}} format")
    tags: list[str] = Field(default_factory=list, description="Tags for the card")
    deck: str | None = Field(default=None, description="Deck name (uses default if not provided)")
    extra: str | None = Field(default=None, description="Additional context/hints")

    @field_validator("text")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip()


class TypeInCard(BaseModel):
    """Type-in answer card (tests exact typing)."""

    front: str = Field(min_length=1, max_length=1000, description="Question or prompt")
    back: str = Field(min_length=1, max_length=500, description="Expected typed answer")
    tags: list[str] = Field(default_factory=list, description="Tags for the card")
    deck: str | None = Field(default=None, description="Deck name (uses default if not provided)")

    @field_validator("front", "back")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip()


class CardBatch(BaseModel):
    """Batch of cards for preview/creation."""

    cards: list[dict] = Field(description="List of card dictionaries")
    deck: str = Field(description="Target deck name")
    source: str | None = Field(default=None, description="Source (PDF filename, URL, etc.)")


# Deck Analysis Models


class DeckPatterns(BaseModel):
    """Deck-level pattern analysis."""

    tag_consistency: float = Field(description="Percentage of cards with tags (0.0-1.0)")
    type_distribution: dict[str, float] = Field(
        description="Distribution of card types (e.g., {'Cloze': 0.68, 'Basic': 0.30})"
    )
    html_usage_percent: float = Field(description="Percentage of cards using HTML formatting")
    avg_field_length: float = Field(description="Average field length in characters")


class QualityReport(BaseModel):
    """Quality analysis report for a deck."""

    score: float = Field(description="Quality score (0-100)")
    total_cards: int = Field(description="Total number of cards analyzed")
    issues_by_severity: dict[str, int] = Field(
        description="Count of issues by severity (error/warning/suggestion)"
    )
    top_issues: list[tuple[str, int]] = Field(
        description="Top 5 most common issues as (issue_type, count) tuples"
    )
    deck_patterns: DeckPatterns = Field(description="Deck-level pattern analysis")
    problematic_card_ids: list[int] = Field(
        description="Note IDs of cards with issues", default_factory=list
    )


class StrugglingCard(BaseModel):
    """Card with performance issues."""

    note_id: int = Field(description="Anki note ID")
    ease: float = Field(description="Ease factor (e.g., 2.5 = 250%)")
    lapses: int = Field(description="Number of times card lapsed")
    interval_days: int = Field(description="Current interval in days")


class PerformanceReport(BaseModel):
    """Performance analysis report for a deck."""

    retention_rate: float = Field(description="Retention rate (0.0-1.0)")
    ease_distribution: dict[str, int] = Field(
        description="Distribution of cards by ease factor buckets"
    )
    lapse_rate: float = Field(description="Percentage of cards with lapses")
    struggling_cards: list[StrugglingCard] = Field(
        description="Cards with low ease or high lapses", default_factory=list
    )
    maturity_breakdown: dict[str, int] = Field(
        description="Distribution by maturity (young/mature/very_mature)"
    )
    total_reviews: int = Field(description="Total number of reviews analyzed", default=0)


class Recommendation(BaseModel):
    """Actionable recommendation for deck improvement."""

    title: str = Field(description="Recommendation title")
    impact: str = Field(description="Impact level: high, medium, or low")
    effort: str = Field(description="Effort level: quick, moderate, or large")
    priority_score: float = Field(description="Priority score (impact/effort)")
    description: str = Field(description="Detailed recommendation description")
    affected_card_ids: list[int] = Field(
        description="Note IDs affected by this recommendation", default_factory=list
    )
    example_before_after: str | None = Field(
        default=None, description="Example showing before/after"
    )
