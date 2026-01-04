"""Card validator that enforces spaced repetition best practices."""

from ..config import settings
from ..models import BasicCard, ClozeCard, TypeInCard, ValidationResult, ValidationSeverity
from .rules import (
    AmbiguityRule,
    AnswerLengthRule,
    ClozeCountRule,
    ClozeFormatRule,
    ContextRule,
    MinimumInformationRule,
)


class CardValidator:
    """Validates cards against best practices for spaced repetition."""

    def __init__(self, strictness: str | None = None):
        """Initialize card validator.

        Args:
            strictness: Validation strictness ('strict', 'moderate', 'lenient').
                       Uses settings.validation_strictness if not provided.
        """
        self.strictness = strictness or settings.validation_strictness
        self.rules = [
            ClozeFormatRule(),  # Must come first (blocks invalid cloze format)
            AnswerLengthRule(),
            MinimumInformationRule(),
            AmbiguityRule(),
            ClozeCountRule(),
            ContextRule(),
        ]

    def validate(self, card: BasicCard | ClozeCard | TypeInCard) -> list[ValidationResult]:
        """Run all validation rules on a card.

        Args:
            card: Card to validate

        Returns:
            List of validation results
        """
        results = []
        for rule in self.rules:
            rule_results = rule.check(card, self.strictness)
            results.extend(rule_results)
        return results

    def is_valid(self, card: BasicCard | ClozeCard | TypeInCard) -> bool:
        """Check if card passes validation (no errors).

        Args:
            card: Card to validate

        Returns:
            True if no ERROR severity results
        """
        results = self.validate(card)
        return not any(r.severity == ValidationSeverity.ERROR for r in results)

    def get_errors(self, card: BasicCard | ClozeCard | TypeInCard) -> list[ValidationResult]:
        """Get only ERROR severity results.

        Args:
            card: Card to validate

        Returns:
            List of error results
        """
        results = self.validate(card)
        return [r for r in results if r.severity == ValidationSeverity.ERROR]

    def get_warnings(self, card: BasicCard | ClozeCard | TypeInCard) -> list[ValidationResult]:
        """Get only WARNING severity results.

        Args:
            card: Card to validate

        Returns:
            List of warning results
        """
        results = self.validate(card)
        return [r for r in results if r.severity == ValidationSeverity.WARNING]

    def get_suggestions(self, card: BasicCard | ClozeCard | TypeInCard) -> list[ValidationResult]:
        """Get only SUGGESTION severity results.

        Args:
            card: Card to validate

        Returns:
            List of suggestion results
        """
        results = self.validate(card)
        return [r for r in results if r.severity == ValidationSeverity.SUGGESTION]


def get_validator(strictness: str | None = None) -> CardValidator:
    """Get a card validator instance.

    Args:
        strictness: Validation strictness level

    Returns:
        CardValidator instance
    """
    return CardValidator(strictness)
