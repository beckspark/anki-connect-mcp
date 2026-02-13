"""MCP tools for LLM memory and reasoning storage.

These tools enable the LLM to maintain context across sessions, store reasoning
for card design decisions, track concept coverage, and learn from user feedback.

Philosophy: The LLM is the brain, MCP is the hands. These tools provide the hands
with memory so the brain can maintain continuity and learn from experience.
"""

import json

from mcp.types import CallToolResult, TextContent

from ..db import get_database
from ..server import app


@app.tool()
async def store_card_rationale(
    anki_note_id: int,
    card_type_reasoning: str,
    wording_notes: str | None = None,
    alternatives_considered: list[str] | None = None,
) -> CallToolResult:
    """Store reasoning for card design decisions.

    Call this after creating a card to record WHY you made specific choices.
    This enables future reflection on card design patterns and continuous improvement.

    Args:
        anki_note_id: Anki note ID of the card
        card_type_reasoning: Why you chose this card type (basic/cloze/type-in)
        wording_notes: Notes about wording decisions (optional)
        alternatives_considered: List of alternative approaches you considered (optional)

    Returns:
        Confirmation message

    Examples:
        >>> store_card_rationale(
        ...     anki_note_id=1234567890,
        ...     card_type_reasoning="Chose cloze because this is a sequence of steps",
        ...     wording_notes="Used active voice for clarity",
        ...     alternatives_considered=["Could have split into multiple basic cards"]
        ... )
    """
    try:
        db = get_database()
        alternatives_json = json.dumps(alternatives_considered) if alternatives_considered else None

        rationale_id = db.store_card_rationale(
            anki_note_id=anki_note_id,
            card_type_reasoning=card_type_reasoning,
            wording_notes=wording_notes,
            alternatives_considered=alternatives_json,
        )

        msg = f"Rationale stored (ID: {rationale_id}) for note {anki_note_id}"
        return CallToolResult(content=[TextContent(type="text", text=msg)])

    except Exception as e:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Failed to store rationale: {str(e)}")],
        )


@app.tool()
async def record_feedback(
    anki_note_id: int,
    feedback_type: str,
    user_comment: str | None = None,
    llm_reflection: str | None = None,
    action_taken: str | None = None,
) -> CallToolResult:
    """Record user feedback and your reflection on a card.

    Use this when a user provides feedback about a card (confusing, too hard, etc.).
    Recording feedback helps you learn from experience and improve future cards.

    Args:
        anki_note_id: Anki note ID of the card
        feedback_type: Type of feedback (e.g., 'confusing', 'too_hard', 'too_easy',
                       'great', 'needs_split', 'wrong_answer', 'needs_context')
        user_comment: User's specific comment (optional)
        llm_reflection: Your analysis of the feedback (optional)
        action_taken: What action was taken in response (optional)

    Returns:
        Confirmation message

    Examples:
        >>> record_feedback(
        ...     anki_note_id=1234567890,
        ...     feedback_type="confusing",
        ...     user_comment="The question is ambiguous",
        ...     llm_reflection="The question could be interpreted two ways",
        ...     action_taken="Rewrote question to be more specific"
        ... )
    """
    try:
        db = get_database()

        feedback_id = db.record_feedback(
            anki_note_id=anki_note_id,
            feedback_type=feedback_type,
            user_comment=user_comment,
            llm_reflection=llm_reflection,
            action_taken=action_taken,
        )

        msg = f"Feedback recorded (ID: {feedback_id}) for note {anki_note_id}"
        msg += f"\nType: {feedback_type}"
        if action_taken:
            msg += f"\nAction taken: {action_taken}"

        return CallToolResult(content=[TextContent(type="text", text=msg)])

    except Exception as e:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Failed to record feedback: {str(e)}")],
        )


@app.tool()
async def link_card_to_concept(
    anki_note_id: int,
    concept_name: str,
    deck: str,
    relationship: str | None = None,
    concept_description: str | None = None,
) -> CallToolResult:
    """Link a card to a concept for coverage tracking.

    Use this to track which concepts are covered by which cards.
    Concepts are automatically created if they don't exist.

    Args:
        anki_note_id: Anki note ID of the card
        concept_name: Name of the concept (e.g., "EHR Interoperability", "HIPAA Compliance")
        deck: Deck the concept belongs to
        relationship: Type of relationship (e.g., 'defines', 'examples', 'contrasts',
                      'applies', 'extends') (optional)
        concept_description: Description if creating a new concept (optional)

    Returns:
        Confirmation message

    Examples:
        >>> link_card_to_concept(
        ...     anki_note_id=1234567890,
        ...     concept_name="EHR Interoperability",
        ...     deck="Health Informatics::Module 02",
        ...     relationship="defines",
        ...     concept_description="The ability of EHR systems to exchange data"
        ... )
    """
    try:
        db = get_database()

        # Create or get concept
        concept_id = db.create_or_get_concept(
            deck=deck,
            name=concept_name,
            description=concept_description,
        )

        # Link card to concept
        db.link_card_to_concept(
            anki_note_id=anki_note_id,
            concept_id=concept_id,
            relationship=relationship,
        )

        msg = f"Card {anki_note_id} linked to concept '{concept_name}'"
        if relationship:
            msg += f" (relationship: {relationship})"

        return CallToolResult(content=[TextContent(type="text", text=msg)])

    except Exception as e:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Failed to link card to concept: {str(e)}")],
        )


@app.tool()
async def get_concept_coverage(deck: str) -> CallToolResult:
    """Get concept coverage for a deck.

    Returns all tracked concepts and how many cards cover each concept.
    Use this to identify coverage gaps before creating new cards.

    Args:
        deck: Deck name to check coverage for

    Returns:
        List of concepts with card counts

    Examples:
        >>> get_concept_coverage(deck="Health Informatics::Module 02")
    """
    try:
        db = get_database()
        concepts = db.get_concept_coverage(deck)

        if not concepts:
            msg = f"No concepts tracked for deck: {deck}\n\n"
            msg += "Start tracking coverage by using link_card_to_concept() after creating cards."
            return CallToolResult(content=[TextContent(type="text", text=msg)])

        msg = f"Concept Coverage for '{deck}':\n\n"

        # Group by coverage level
        well_covered = []
        sparse = []
        uncovered = []

        for concept in concepts:
            if concept["card_count"] >= 3:
                well_covered.append(concept)
            elif concept["card_count"] >= 1:
                sparse.append(concept)
            else:
                uncovered.append(concept)

        if well_covered:
            msg += "Well Covered (3+ cards):\n"
            for c in well_covered:
                desc = f" - {c['description']}" if c["description"] else ""
                msg += f"  - {c['name']}: {c['card_count']} cards{desc}\n"
            msg += "\n"

        if sparse:
            msg += "Sparse Coverage (1-2 cards):\n"
            for c in sparse:
                desc = f" - {c['description']}" if c["description"] else ""
                msg += f"  - {c['name']}: {c['card_count']} cards{desc}\n"
            msg += "\n"

        if uncovered:
            msg += "Defined but Uncovered (0 cards):\n"
            for c in uncovered:
                desc = f" - {c['description']}" if c["description"] else ""
                msg += f"  - {c['name']}{desc}\n"
            msg += "\n"

        msg += f"Total: {len(concepts)} concepts tracked"

        return CallToolResult(content=[TextContent(type="text", text=msg)])

    except Exception as e:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Failed to get concept coverage: {str(e)}")],
        )


@app.tool()
async def save_session_context(
    deck: str,
    source_material: str | None = None,
    learning_goals: str | None = None,
    coverage_strategy: str | None = None,
    observations: str | None = None,
) -> CallToolResult:
    """Save session context for future continuity.

    Call this at the end of a card creation session to preserve context
    for future sessions. This enables you to pick up where you left off.

    Args:
        deck: Deck name
        source_material: What source material was used (e.g., PDF filename, chapter)
        learning_goals: User's stated learning goals
        coverage_strategy: Your planned coverage strategy
        observations: Patterns or insights you noticed during the session

    Returns:
        Confirmation message

    Examples:
        >>> save_session_context(
        ...     deck="Health Informatics::Module 02",
        ...     source_material="Module 02 PDF: Evolution of EHRs",
        ...     learning_goals="Understand EHR history and current state",
        ...     coverage_strategy="10 cards: 3 history, 3 technical, 2 regulatory, 2 trends",
        ...     observations="User prefers concise answers; module heavy on acronyms"
        ... )
    """
    try:
        db = get_database()

        session_id = db.save_session_context(
            deck=deck,
            source_material=source_material,
            learning_goals=learning_goals,
            coverage_strategy=coverage_strategy,
            observations=observations,
        )

        msg = f"Session context saved (ID: {session_id}) for deck: {deck}"
        return CallToolResult(content=[TextContent(type="text", text=msg)])

    except Exception as e:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Failed to save session context: {str(e)}")],
        )


@app.tool()
async def get_session_context(deck: str, limit: int = 3) -> CallToolResult:
    """Get recent session context for a deck.

    Call this at the start of a session to recall previous context,
    enabling continuity across conversations.

    Args:
        deck: Deck name
        limit: Maximum number of recent sessions to return (default: 3)

    Returns:
        Recent session context

    Examples:
        >>> get_session_context(deck="Health Informatics::Module 02")
    """
    try:
        db = get_database()
        sessions = db.get_session_context(deck, limit)

        if not sessions:
            msg = f"No previous session context for deck: {deck}\n\n"
            msg += "This appears to be a new deck. "
            msg += "Save context with save_session_context() at the end of this session."
            return CallToolResult(content=[TextContent(type="text", text=msg)])

        msg = f"Previous Session Context for '{deck}':\n\n"

        for i, session in enumerate(sessions, 1):
            msg += f"--- Session {i} ({session['created_at']}) ---\n"

            if session["source_material"]:
                msg += f"Source: {session['source_material']}\n"
            if session["learning_goals"]:
                msg += f"Goals: {session['learning_goals']}\n"
            if session["coverage_strategy"]:
                msg += f"Strategy: {session['coverage_strategy']}\n"
            if session["observations"]:
                msg += f"Observations: {session['observations']}\n"

            msg += "\n"

        return CallToolResult(content=[TextContent(type="text", text=msg.strip())])

    except Exception as e:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Failed to get session context: {str(e)}")],
        )
