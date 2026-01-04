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
