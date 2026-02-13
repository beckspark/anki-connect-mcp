"""DuckDB database for tracking card generation history."""

import json
from pathlib import Path

import duckdb

from ..config import settings


class Database:
    """DuckDB database manager for card history tracking."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        """Initialize database manager.

        Args:
            conn: DuckDB connection
        """
        self.conn = conn

    def create_generation(
        self, source_type: str, source_path: str | None = None, metadata: dict | None = None
    ) -> int:
        """Create a new generation session.

        Args:
            source_type: Type of source ('pdf', 'epub', 'web', 'text', 'manual')
            source_path: File path or URL of source
            metadata: Additional metadata (page range, chapters, etc.) as JSON

        Returns:
            Generation ID
        """
        metadata_json = json.dumps(metadata) if metadata else None
        result = self.conn.execute(
            """
            INSERT INTO generations (source_type, source_path, source_metadata)
            VALUES (?, ?, ?)
            RETURNING id
            """,
            [source_type, source_path, metadata_json],
        ).fetchone()
        if result is None:
            raise RuntimeError("Failed to create generation record")
        return result[0]

    def add_generated_card(
        self,
        generation_id: int,
        anki_note_id: int,
        card_type: str,
        front_or_text: str,
        back: str | None,
        deck: str,
        tags: list[str] | None = None,
        validation_warnings: list[dict] | None = None,
    ) -> int:
        """Link an Anki card to a generation session.

        Args:
            generation_id: Generation session ID
            anki_note_id: Anki note ID
            card_type: Card type ('basic', 'cloze', 'type_in')
            front_or_text: Front text (or cloze text)
            back: Back text (None for cloze cards)
            deck: Deck name
            tags: List of tags
            validation_warnings: Validation warnings as JSON

        Returns:
            Generated card ID
        """
        tags_json = json.dumps(tags) if tags else None
        warnings_json = json.dumps(validation_warnings) if validation_warnings else None

        result = self.conn.execute(
            """
            INSERT INTO generated_cards (
                generation_id, anki_note_id, card_type,
                front_or_text, back, deck, tags, validation_warnings
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [
                generation_id,
                anki_note_id,
                card_type,
                front_or_text,
                back,
                deck,
                tags_json,
                warnings_json,
            ],
        ).fetchone()
        if result is None:
            raise RuntimeError("Failed to add generated card")
        return result[0]

    def get_generation_history(self, source_type: str | None = None, limit: int = 50) -> list[dict]:
        """Get recent generation history.

        Args:
            source_type: Filter by source type (None for all)
            limit: Maximum number of results

        Returns:
            List of generation records with card counts
        """
        if source_type:
            query = """
                SELECT
                    g.id,
                    g.source_type,
                    g.source_path,
                    g.source_metadata,
                    g.generated_at,
                    COUNT(gc.id) as card_count
                FROM generations g
                LEFT JOIN generated_cards gc ON g.id = gc.generation_id
                WHERE g.source_type = ?
                GROUP BY g.id, g.source_type, g.source_path, g.source_metadata, g.generated_at
                ORDER BY g.generated_at DESC
                LIMIT ?
            """
            result = self.conn.execute(query, [source_type, limit]).fetchall()
        else:
            query = """
                SELECT
                    g.id,
                    g.source_type,
                    g.source_path,
                    g.source_metadata,
                    g.generated_at,
                    COUNT(gc.id) as card_count
                FROM generations g
                LEFT JOIN generated_cards gc ON g.id = gc.generation_id
                GROUP BY g.id, g.source_type, g.source_path, g.source_metadata, g.generated_at
                ORDER BY g.generated_at DESC
                LIMIT ?
            """
            result = self.conn.execute(query, [limit]).fetchall()

        columns = [
            "id",
            "source_type",
            "source_path",
            "source_metadata",
            "generated_at",
            "card_count",
        ]
        return [dict(zip(columns, row)) for row in result]

    def get_cards_by_source(self, source_path: str) -> list[dict]:
        """Get all cards generated from a specific source.

        Args:
            source_path: Source file path or URL

        Returns:
            List of card records
        """
        query = """
            SELECT
                gc.id,
                gc.anki_note_id,
                gc.card_type,
                gc.front_or_text,
                gc.back,
                gc.deck,
                gc.tags,
                gc.validation_warnings,
                gc.created_at,
                g.source_type
            FROM generated_cards gc
            JOIN generations g ON gc.generation_id = g.id
            WHERE g.source_path = ?
            ORDER BY gc.created_at DESC
        """
        result = self.conn.execute(query, [source_path]).fetchall()

        columns = [
            "id",
            "anki_note_id",
            "card_type",
            "front_or_text",
            "back",
            "deck",
            "tags",
            "validation_warnings",
            "created_at",
            "source_type",
        ]
        return [dict(zip(columns, row)) for row in result]

    def get_recent_cards(self, limit: int = 50) -> list[dict]:
        """Get recently created cards.

        Args:
            limit: Maximum number of results

        Returns:
            List of card records
        """
        query = """
            SELECT
                gc.id,
                gc.anki_note_id,
                gc.card_type,
                gc.front_or_text,
                gc.back,
                gc.deck,
                gc.created_at,
                g.source_type,
                g.source_path
            FROM generated_cards gc
            JOIN generations g ON gc.generation_id = g.id
            ORDER BY gc.created_at DESC
            LIMIT ?
        """
        result = self.conn.execute(query, [limit]).fetchall()

        columns = [
            "id",
            "anki_note_id",
            "card_type",
            "front_or_text",
            "back",
            "deck",
            "created_at",
            "source_type",
            "source_path",
        ]
        return [dict(zip(columns, row)) for row in result]

    def get_validation_stats(self) -> dict:
        """Get aggregated validation statistics.

        Returns:
            Dictionary with validation warning counts and patterns
        """
        # Get total cards
        total_result = self.conn.execute("SELECT COUNT(*) FROM generated_cards").fetchone()
        total = total_result[0] if total_result else 0

        # Get cards with warnings
        warnings_result = self.conn.execute(
            "SELECT COUNT(*) FROM generated_cards WHERE validation_warnings IS NOT NULL"
        ).fetchone()
        with_warnings = warnings_result[0] if warnings_result else 0

        # Get most common warning types (this would need more complex parsing)
        # For now, just return basic stats
        return {
            "total_cards": total,
            "cards_with_warnings": with_warnings,
            "warning_rate": round(with_warnings / total * 100, 2) if total > 0 else 0,
        }

    def save_deck_analysis(
        self,
        deck_name: str,
        analysis_type: str,
        overall_score: float | None,
        total_cards: int,
        metadata: dict | None = None,
    ) -> int:
        """Save deck analysis results.

        Args:
            deck_name: Name of the analyzed deck
            analysis_type: Type of analysis ('quality', 'performance', 'recommendations')
            overall_score: Overall score (0-100 for quality, 0.0-1.0 for performance)
            total_cards: Number of cards analyzed
            metadata: Additional analysis metadata as JSON

        Returns:
            Analysis ID
        """
        metadata_json = json.dumps(metadata) if metadata else None
        result = self.conn.execute(
            """
            INSERT INTO deck_analyses
            (deck_name, analysis_type, overall_score, total_cards, metadata)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id
            """,
            [deck_name, analysis_type, overall_score, total_cards, metadata_json],
        ).fetchone()
        if result is None:
            raise RuntimeError("Failed to save deck analysis")
        return result[0]

    def get_analysis_history(self, deck_name: str, limit: int = 10) -> list[dict]:
        """Get historical analysis runs for a deck.

        Args:
            deck_name: Name of the deck
            limit: Maximum number of results

        Returns:
            List of analysis records ordered by date (most recent first)
        """
        query = """
            SELECT
                id,
                deck_name,
                analysis_type,
                overall_score,
                total_cards,
                metadata,
                analyzed_at
            FROM deck_analyses
            WHERE deck_name = ?
            ORDER BY analyzed_at DESC
            LIMIT ?
        """
        result = self.conn.execute(query, [deck_name, limit]).fetchall()

        columns = [
            "id",
            "deck_name",
            "analysis_type",
            "overall_score",
            "total_cards",
            "metadata",
            "analyzed_at",
        ]
        return [dict(zip(columns, row)) for row in result]

    # ========== LLM Memory Methods ==========

    def create_or_get_concept(
        self,
        deck: str,
        name: str,
        description: str | None = None,
        parent_concept_id: int | None = None,
    ) -> int:
        """Create a concept or return existing concept ID.

        Args:
            deck: Deck this concept belongs to
            name: Concept name
            description: Optional description
            parent_concept_id: Optional parent concept for hierarchy

        Returns:
            Concept ID (existing or newly created)
        """
        # Check if concept already exists
        existing = self.conn.execute(
            "SELECT id FROM concepts WHERE deck = ? AND name = ?", [deck, name]
        ).fetchone()

        if existing:
            return existing[0]

        # Create new concept
        result = self.conn.execute(
            """
            INSERT INTO concepts (deck, name, description, parent_concept_id)
            VALUES (?, ?, ?, ?)
            RETURNING id
            """,
            [deck, name, description, parent_concept_id],
        ).fetchone()
        if result is None:
            raise RuntimeError("Failed to create concept")
        return result[0]

    def link_card_to_concept(
        self, anki_note_id: int, concept_id: int, relationship: str | None = None
    ) -> None:
        """Link an Anki card to a concept.

        Args:
            anki_note_id: Anki note ID
            concept_id: Concept ID
            relationship: Type of relationship (e.g., 'defines', 'examples', 'contrasts')
        """
        # Use INSERT OR REPLACE to handle duplicates
        self.conn.execute(
            """
            INSERT OR REPLACE INTO card_concepts (anki_note_id, concept_id, relationship)
            VALUES (?, ?, ?)
            """,
            [anki_note_id, concept_id, relationship],
        )

    def get_concept_coverage(self, deck: str) -> list[dict]:
        """Get concepts and their card coverage for a deck.

        Args:
            deck: Deck name

        Returns:
            List of concepts with card counts
        """
        query = """
            SELECT
                c.id,
                c.name,
                c.description,
                c.parent_concept_id,
                COUNT(cc.anki_note_id) as card_count
            FROM concepts c
            LEFT JOIN card_concepts cc ON c.id = cc.concept_id
            WHERE c.deck = ?
            GROUP BY c.id, c.name, c.description, c.parent_concept_id
            ORDER BY c.name
        """
        result = self.conn.execute(query, [deck]).fetchall()

        columns = ["id", "name", "description", "parent_concept_id", "card_count"]
        return [dict(zip(columns, row)) for row in result]

    def store_card_rationale(
        self,
        anki_note_id: int,
        card_type_reasoning: str | None = None,
        wording_notes: str | None = None,
        alternatives_considered: str | None = None,
    ) -> int:
        """Store reasoning for card design decisions.

        Args:
            anki_note_id: Anki note ID
            card_type_reasoning: Why this card type was chosen
            wording_notes: Notes about wording decisions
            alternatives_considered: JSON string of alternatives that were considered

        Returns:
            Rationale record ID
        """
        result = self.conn.execute(
            """
            INSERT INTO card_rationale
            (anki_note_id, card_type_reasoning, wording_notes, alternatives_considered)
            VALUES (?, ?, ?, ?)
            RETURNING id
            """,
            [anki_note_id, card_type_reasoning, wording_notes, alternatives_considered],
        ).fetchone()
        if result is None:
            raise RuntimeError("Failed to store card rationale")
        return result[0]

    def get_card_rationale(self, anki_note_id: int) -> dict | None:
        """Get stored rationale for a card.

        Args:
            anki_note_id: Anki note ID

        Returns:
            Rationale record or None
        """
        query = """
            SELECT
                id, anki_note_id, card_type_reasoning,
                wording_notes, alternatives_considered, created_at
            FROM card_rationale
            WHERE anki_note_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """
        result = self.conn.execute(query, [anki_note_id]).fetchone()
        if not result:
            return None

        columns = [
            "id",
            "anki_note_id",
            "card_type_reasoning",
            "wording_notes",
            "alternatives_considered",
            "created_at",
        ]
        return dict(zip(columns, result))

    def record_feedback(
        self,
        anki_note_id: int,
        feedback_type: str,
        user_comment: str | None = None,
        llm_reflection: str | None = None,
        action_taken: str | None = None,
    ) -> int:
        """Record user feedback and LLM reflection.

        Args:
            anki_note_id: Anki note ID
            feedback_type: Type of feedback (e.g., 'confusing', 'too_hard', 'great')
            user_comment: User's comment
            llm_reflection: LLM's analysis of the feedback
            action_taken: What action was taken in response

        Returns:
            Feedback record ID
        """
        result = self.conn.execute(
            """
            INSERT INTO card_feedback
            (anki_note_id, feedback_type, user_comment, llm_reflection, action_taken)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id
            """,
            [anki_note_id, feedback_type, user_comment, llm_reflection, action_taken],
        ).fetchone()
        if result is None:
            raise RuntimeError("Failed to record feedback")
        return result[0]

    def get_card_feedback(self, anki_note_id: int) -> list[dict]:
        """Get all feedback for a card.

        Args:
            anki_note_id: Anki note ID

        Returns:
            List of feedback records
        """
        query = """
            SELECT
                id, anki_note_id, feedback_type, user_comment,
                llm_reflection, action_taken, created_at
            FROM card_feedback
            WHERE anki_note_id = ?
            ORDER BY created_at DESC
        """
        result = self.conn.execute(query, [anki_note_id]).fetchall()

        columns = [
            "id",
            "anki_note_id",
            "feedback_type",
            "user_comment",
            "llm_reflection",
            "action_taken",
            "created_at",
        ]
        return [dict(zip(columns, row)) for row in result]

    def save_session_context(
        self,
        deck: str,
        source_material: str | None = None,
        learning_goals: str | None = None,
        coverage_strategy: str | None = None,
        observations: str | None = None,
    ) -> int:
        """Save session context for future continuity.

        Args:
            deck: Deck name
            source_material: What source material was used
            learning_goals: User's stated learning goals
            coverage_strategy: LLM's planned coverage strategy
            observations: Patterns or insights noticed

        Returns:
            Session ID
        """
        result = self.conn.execute(
            """
            INSERT INTO sessions
            (deck, source_material, learning_goals, coverage_strategy, observations)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id
            """,
            [deck, source_material, learning_goals, coverage_strategy, observations],
        ).fetchone()
        if result is None:
            raise RuntimeError("Failed to save session context")
        return result[0]

    def get_session_context(self, deck: str, limit: int = 5) -> list[dict]:
        """Get recent session context for a deck.

        Args:
            deck: Deck name
            limit: Maximum number of sessions to return

        Returns:
            List of session records (most recent first)
        """
        query = """
            SELECT
                id, deck, source_material, learning_goals,
                coverage_strategy, observations, created_at
            FROM sessions
            WHERE deck = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        result = self.conn.execute(query, [deck, limit]).fetchall()

        columns = [
            "id",
            "deck",
            "source_material",
            "learning_goals",
            "coverage_strategy",
            "observations",
            "created_at",
        ]
        return [dict(zip(columns, row)) for row in result]


def _init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Initialize database schema.

    Args:
        conn: DuckDB connection
    """
    # Create sequences for auto-incrementing IDs
    conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_generations_id START 1")
    conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_generated_cards_id START 1")
    conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_deck_analyses_id START 1")
    conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_concepts_id START 1")
    conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_card_rationale_id START 1")
    conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_card_feedback_id START 1")
    conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_sessions_id START 1")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS generations (
            id BIGINT PRIMARY KEY DEFAULT nextval('seq_generations_id'),
            source_type TEXT NOT NULL,
            source_path TEXT,
            source_metadata TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS generated_cards (
            id BIGINT PRIMARY KEY DEFAULT nextval('seq_generated_cards_id'),
            generation_id BIGINT,
            anki_note_id BIGINT NOT NULL,
            card_type TEXT NOT NULL,
            front_or_text TEXT NOT NULL,
            back TEXT,
            deck TEXT NOT NULL,
            tags TEXT,
            validation_warnings TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (generation_id) REFERENCES generations(id)
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS deck_analyses (
            id BIGINT PRIMARY KEY DEFAULT nextval('seq_deck_analyses_id'),
            deck_name TEXT NOT NULL,
            analysis_type TEXT NOT NULL,
            overall_score FLOAT,
            total_cards INTEGER,
            metadata TEXT,
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # LLM Memory Tables - for concept coverage and reasoning storage

    # Concepts: What concepts exist and their relationships
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS concepts (
            id BIGINT PRIMARY KEY DEFAULT nextval('seq_concepts_id'),
            deck TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            parent_concept_id BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_concept_id) REFERENCES concepts(id)
        )
    """
    )

    # Card-Concept links: Which cards cover which concepts (many-to-many)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS card_concepts (
            anki_note_id BIGINT NOT NULL,
            concept_id BIGINT NOT NULL,
            relationship TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (anki_note_id, concept_id),
            FOREIGN KEY (concept_id) REFERENCES concepts(id)
        )
    """
    )

    # Card Rationale: Store LLM reasoning for card design decisions
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS card_rationale (
            id BIGINT PRIMARY KEY DEFAULT nextval('seq_card_rationale_id'),
            anki_note_id BIGINT NOT NULL,
            card_type_reasoning TEXT,
            wording_notes TEXT,
            alternatives_considered TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Card Feedback: User feedback and LLM reflection for learning
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS card_feedback (
            id BIGINT PRIMARY KEY DEFAULT nextval('seq_card_feedback_id'),
            anki_note_id BIGINT NOT NULL,
            feedback_type TEXT NOT NULL,
            user_comment TEXT,
            llm_reflection TEXT,
            action_taken TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Sessions: Context for continuity across conversations
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id BIGINT PRIMARY KEY DEFAULT nextval('seq_sessions_id'),
            deck TEXT NOT NULL,
            source_material TEXT,
            learning_goals TEXT,
            coverage_strategy TEXT,
            observations TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create indices for common queries
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_generated_cards_generation
        ON generated_cards(generation_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_generated_cards_created
        ON generated_cards(created_at DESC)
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_generations_source ON generations(source_path)")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_deck_analyses_deck
        ON deck_analyses(deck_name, analyzed_at DESC)
        """
    )

    # LLM Memory indices
    conn.execute("CREATE INDEX IF NOT EXISTS idx_concepts_deck ON concepts(deck)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_card_concepts_note ON card_concepts(anki_note_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_card_rationale_note ON card_rationale(anki_note_id)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_card_feedback_note ON card_feedback(anki_note_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_deck ON sessions(deck, created_at DESC)")


# Singleton connection
_conn: duckdb.DuckDBPyConnection | None = None


def get_db_connection() -> duckdb.DuckDBPyConnection:
    """Get or create the singleton DuckDB connection.

    Returns:
        Singleton DuckDB connection
    """
    global _conn
    if _conn is None:
        db_path = Path(settings.database_path).expanduser()
        _conn = duckdb.connect(str(db_path))
        _init_schema(_conn)
    return _conn


def get_database() -> Database:
    """Get Database instance with singleton connection.

    Returns:
        Database instance
    """
    return Database(get_db_connection())
