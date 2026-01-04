"""Validation rules for flashcard quality enforcement."""

import re
from abc import ABC, abstractmethod

from ..models import BasicCard, ClozeCard, TypeInCard, ValidationResult, ValidationSeverity


class ValidationRule(ABC):
    """Base class for validation rules."""

    @abstractmethod
    def check(
        self, card: BasicCard | ClozeCard | TypeInCard, strictness: str
    ) -> list[ValidationResult]:
        """Check card against this rule.

        Args:
            card: Card to validate
            strictness: Validation strictness level ('strict', 'moderate', 'lenient')

        Returns:
            List of validation results
        """


class AnswerLengthRule(ValidationRule):
    """Ensure answers aren't too long (violates minimum information principle)."""

    def check(
        self, card: BasicCard | ClozeCard | TypeInCard, strictness: str
    ) -> list[ValidationResult]:
        """Check answer length."""
        if isinstance(card, ClozeCard):
            return []  # Cloze cards don't have separate answers

        # Get max words based on strictness
        max_words = {"strict": 30, "moderate": 50, "lenient": 100}[strictness]

        word_count = len(card.back.split())
        if word_count > max_words:
            return [
                ValidationResult(
                    severity=ValidationSeverity.WARNING,
                    rule="answer_length",
                    message=(
                        f"Answer has {word_count} words (max recommended: {max_words}). "
                        "Consider splitting into multiple cards following "
                        "the minimum information principle."
                    ),
                    field="back",
                )
            ]
        return []


class MinimumInformationRule(ValidationRule):
    """Detect cards asking multiple questions (violates minimum information principle)."""

    def check(
        self, card: BasicCard | ClozeCard | TypeInCard, strictness: str
    ) -> list[ValidationResult]:
        """Check for multiple concepts in one card."""
        if isinstance(card, ClozeCard):
            # Check number of cloze deletions
            clozes = re.findall(r"\{\{c\d+::", card.text)
            if len(clozes) > 3:
                return [
                    ValidationResult(
                        severity=ValidationSeverity.WARNING,
                        rule="minimum_information",
                        message=f"Card has {len(clozes)} cloze deletions. "
                        f"Consider splitting into separate cards for better retention.",
                        field="text",
                    )
                ]
            return []

        # For basic/type-in cards, look for multiple questions or lists
        front = card.front.lower()
        triggers = [
            ("list", "enumerate"),  # List prompts
            ("and", ","),  # Multiple items
            ("or",),  # Multiple choices
        ]

        found_triggers = []
        for trigger_group in triggers:
            if any(t in front for t in trigger_group):
                found_triggers.extend([t for t in trigger_group if t in front])

        if len(found_triggers) >= 2:
            severity = (
                ValidationSeverity.WARNING
                if strictness == "strict"
                else ValidationSeverity.SUGGESTION
            )
            return [
                ValidationResult(
                    severity=severity,
                    rule="minimum_information",
                    message="Front may contain multiple questions or list requests. "
                    "One concept per card improves retention.",
                    field="front",
                )
            ]
        return []


class AmbiguityRule(ValidationRule):
    """Flag vague or ambiguous questions."""

    def check(
        self, card: BasicCard | ClozeCard | TypeInCard, strictness: str
    ) -> list[ValidationResult]:
        """Check for question ambiguity."""
        if isinstance(card, ClozeCard):
            return []  # Cloze cards are inherently specific

        # Check for vague question patterns
        front_lower = card.front.lower()
        vague_patterns = [
            "what about",
            "tell me about",
            "describe",
            "explain everything",
            "what do you know",
        ]

        for pattern in vague_patterns:
            if pattern in front_lower:
                return [
                    ValidationResult(
                        severity=ValidationSeverity.SUGGESTION,
                        rule="ambiguity",
                        message=(
                            f"Question contains '{pattern}' which may be too vague. "
                            "Be more specific (e.g., 'What is the function of...' "
                            "instead of 'What about...')."
                        ),
                        field="front",
                    )
                ]

        # Check if question is too short (might be incomplete)
        if len(card.front.strip()) < 10:
            return [
                ValidationResult(
                    severity=ValidationSeverity.SUGGESTION,
                    rule="ambiguity",
                    message=(
                        "Question is very short. "
                        "Ensure it provides enough context for standalone understanding."
                    ),
                    field="front",
                )
            ]

        return []


class ClozeCountRule(ValidationRule):
    """Warn if too many cloze deletions in one card."""

    def check(
        self, card: BasicCard | ClozeCard | TypeInCard, strictness: str
    ) -> list[ValidationResult]:
        """Check cloze deletion count."""
        if not isinstance(card, ClozeCard):
            return []

        clozes = re.findall(r"\{\{c\d+::", card.text)
        max_clozes = {"strict": 2, "moderate": 3, "lenient": 5}[strictness]

        if len(clozes) > max_clozes:
            return [
                ValidationResult(
                    severity=ValidationSeverity.WARNING,
                    rule="cloze_count",
                    message=(
                        f"Card has {len(clozes)} cloze deletions "
                        f"(max recommended: {max_clozes}). "
                        "Too many deletions make cards difficult and violate "
                        "minimum information principle."
                    ),
                    field="text",
                )
            ]
        return []


class ClozeFormatRule(ValidationRule):
    """Validate cloze deletion format."""

    def check(
        self, card: BasicCard | ClozeCard | TypeInCard, strictness: str
    ) -> list[ValidationResult]:
        """Check cloze format validity."""
        if not isinstance(card, ClozeCard):
            return []

        # Check if there are any cloze deletions at all
        if not re.search(r"\{\{c\d+::", card.text):
            return [
                ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule="cloze_format",
                    message=(
                        "Cloze card must contain at least one cloze deletion "
                        "in {{c1::text}} format."
                    ),
                    field="text",
                )
            ]

        # Check for malformed cloze deletions
        malformed = re.findall(r"\{\{[^c]|c\d+:[^:]|\{\{c\d+:[^\}]*$", card.text)
        if malformed:
            return [
                ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    rule="cloze_format",
                    message=(
                        "Malformed cloze deletion. "
                        "Use format: {{c1::text}} or {{c1::text::hint}}"
                    ),
                    field="text",
                )
            ]

        return []


class ContextRule(ValidationRule):
    """Ensure cards have enough context for standalone comprehension."""

    def check(
        self, card: BasicCard | ClozeCard | TypeInCard, strictness: str
    ) -> list[ValidationResult]:
        """Check for sufficient context."""
        if isinstance(card, ClozeCard):
            # For cloze cards, check if text is too short
            if len(card.text.replace("{{", "").replace("}}", "").strip()) < 20:
                return [
                    ValidationResult(
                        severity=ValidationSeverity.SUGGESTION,
                        rule="context",
                        message=(
                            "Cloze text is very short. "
                            "Consider adding context for standalone understanding."
                        ),
                        field="text",
                    )
                ]
            return []

        # For basic cards, check if front is a bare word (no context)
        if len(card.front.split()) <= 2 and "?" not in card.front:
            return [
                ValidationResult(
                    severity=ValidationSeverity.SUGGESTION,
                    rule="context",
                    message="Question lacks context. Add details for standalone comprehension "
                    "(e.g., 'Capital of France?' instead of 'France').",
                    field="front",
                )
            ]

        return []
