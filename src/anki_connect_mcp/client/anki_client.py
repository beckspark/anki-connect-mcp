"""AnkiConnect HTTP client with singleton pattern."""

from typing import Any

import httpx

from ..config import settings


class AnkiConnectionError(Exception):
    """Raised when unable to connect to AnkiConnect."""


class AnkiAPIError(Exception):
    """Raised when AnkiConnect API returns an error."""


class AnkiClient:
    """Async HTTP client for AnkiConnect API."""

    def __init__(self, url: str | None = None, version: int | None = None):
        """Initialize AnkiConnect client.

        Args:
            url: AnkiConnect API endpoint
            version: AnkiConnect API version
        """
        self.url = url or settings.anki_connect_url
        self.version = version or settings.anki_connect_version

    async def invoke(self, action: str, params: dict[str, Any] | None = None) -> Any:
        """Call AnkiConnect API action.

        Args:
            action: API action name
            params: Action parameters

        Returns:
            API response result

        Raises:
            AnkiConnectionError: Failed to connect to Anki
            AnkiAPIError: API returned an error
        """
        payload = {"action": action, "version": self.version, "params": params or {}}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, json=payload, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                if result.get("error"):
                    raise AnkiAPIError(result["error"])

                return result.get("result")

            except httpx.HTTPError as e:
                raise AnkiConnectionError(
                    f"Failed to connect to AnkiConnect at {self.url}. "
                    f"Is Anki running with AnkiConnect installed? Error: {e}"
                ) from e

    # Note operations
    async def add_note(self, note: dict) -> int:
        """Add a single note.

        Args:
            note: Note object with deckName, modelName, fields, tags

        Returns:
            Note ID

        Raises:
            AnkiConnectionError: Connection failed
            AnkiAPIError: Note creation failed
        """
        return await self.invoke("addNote", {"note": note})

    async def add_notes(self, notes: list[dict]) -> list[int | None]:
        """Add multiple notes.

        Args:
            notes: List of note objects

        Returns:
            List of note IDs (None for failures)

        Raises:
            AnkiConnectionError: Connection failed
        """
        return await self.invoke("addNotes", {"notes": notes})

    async def update_note_fields(self, note_id: int, fields: dict[str, str]) -> None:
        """Update fields of an existing note.

        Args:
            note_id: Note ID to update
            fields: Dictionary of field names to values

        Raises:
            AnkiConnectionError: Connection failed
            AnkiAPIError: Update failed
        """
        await self.invoke("updateNoteFields", {"note": {"id": note_id, "fields": fields}})

    async def find_notes(self, query: str) -> list[int]:
        """Find note IDs matching query.

        Args:
            query: Anki search query

        Returns:
            List of note IDs

        Raises:
            AnkiConnectionError: Connection failed
        """
        return await self.invoke("findNotes", {"query": query})

    async def notes_info(self, note_ids: list[int]) -> list[dict]:
        """Get information about notes.

        Args:
            note_ids: List of note IDs

        Returns:
            List of note info dictionaries

        Raises:
            AnkiConnectionError: Connection failed
        """
        return await self.invoke("notesInfo", {"notes": note_ids})

    # Deck operations
    async def deck_names(self) -> list[str]:
        """Get all deck names.

        Returns:
            List of deck names

        Raises:
            AnkiConnectionError: Connection failed
        """
        return await self.invoke("deckNames")

    async def deck_names_and_ids(self) -> dict[str, int]:
        """Get deck names mapped to IDs.

        Returns:
            Dictionary mapping deck names to deck IDs

        Raises:
            AnkiConnectionError: Connection failed
        """
        return await self.invoke("deckNamesAndIds")

    async def create_deck(self, name: str) -> int:
        """Create a new deck.

        Args:
            name: Deck name (supports hierarchy with ::)

        Returns:
            Deck ID

        Raises:
            AnkiConnectionError: Connection failed
        """
        return await self.invoke("createDeck", {"deck": name})

    async def delete_decks(self, deck_names: list[str], cards_too: bool = False) -> None:
        """Delete decks.

        Args:
            deck_names: List of deck names to delete
            cards_too: Whether to delete cards as well

        Raises:
            AnkiConnectionError: Connection failed
        """
        await self.invoke("deleteDecks", {"decks": deck_names, "cardsToo": cards_too})

    async def get_deck_stats(self, deck_name: str) -> dict:
        """Get statistics for a deck.

        Args:
            deck_name: Deck name

        Returns:
            Dictionary with deck statistics (new, learning, review counts)

        Raises:
            AnkiConnectionError: Connection failed
        """
        return await self.invoke("getDeckStats", {"decks": [deck_name]})

    # Model (note type) operations
    async def model_names(self) -> list[str]:
        """Get all model (note type) names.

        Returns:
            List of model names

        Raises:
            AnkiConnectionError: Connection failed
        """
        return await self.invoke("modelNames")

    async def model_names_and_ids(self) -> dict[str, int]:
        """Get model names mapped to IDs.

        Returns:
            Dictionary mapping model names to model IDs

        Raises:
            AnkiConnectionError: Connection failed
        """
        return await self.invoke("modelNamesAndIds")

    async def model_field_names(self, model_name: str) -> list[str]:
        """Get field names for a model.

        Args:
            model_name: Model name

        Returns:
            List of field names

        Raises:
            AnkiConnectionError: Connection failed
        """
        return await self.invoke("modelFieldNames", {"modelName": model_name})

    # Card operations
    async def find_cards(self, query: str) -> list[int]:
        """Find card IDs matching query.

        Args:
            query: Anki search query

        Returns:
            List of card IDs

        Raises:
            AnkiConnectionError: Connection failed
        """
        return await self.invoke("findCards", {"query": query})

    async def cards_info(self, card_ids: list[int]) -> list[dict]:
        """Get information about cards.

        Args:
            card_ids: List of card IDs

        Returns:
            List of card info dictionaries

        Raises:
            AnkiConnectionError: Connection failed
        """
        return await self.invoke("cardsInfo", {"cards": card_ids})

    async def get_reviews_of_cards(self, card_ids: list[int]) -> dict:
        """Get review history for cards.

        Args:
            card_ids: List of card IDs

        Returns:
            Dictionary mapping card IDs to review history

        Raises:
            AnkiConnectionError: Connection failed
        """
        return await self.invoke("getReviewsOfCards", {"cards": card_ids})

    # Tag operations
    async def add_tags(self, note_ids: list[int], tags: str) -> None:
        """Add tags to notes.

        Args:
            note_ids: List of note IDs to add tags to
            tags: Space-separated string of tags to add

        Raises:
            AnkiConnectionError: Connection failed
        """
        await self.invoke("addTags", {"notes": note_ids, "tags": tags})

    async def remove_tags(self, note_ids: list[int], tags: str) -> None:
        """Remove tags from notes.

        Args:
            note_ids: List of note IDs to remove tags from
            tags: Space-separated string of tags to remove

        Raises:
            AnkiConnectionError: Connection failed
        """
        await self.invoke("removeTags", {"notes": note_ids, "tags": tags})

    async def replace_tags(
        self, note_ids: list[int], tag_to_replace: str, replace_with: str
    ) -> None:
        """Replace tags in notes.

        Args:
            note_ids: List of note IDs to modify
            tag_to_replace: Tag to replace
            replace_with: Tag to replace with

        Raises:
            AnkiConnectionError: Connection failed
        """
        await self.invoke(
            "replaceTags",
            {"notes": note_ids, "tag_to_replace": tag_to_replace, "replace_with_tag": replace_with},
        )

    async def get_note_tags(self, note_id: int) -> list[str]:
        """Get tags for a note.

        Args:
            note_id: Note ID

        Returns:
            List of tags

        Raises:
            AnkiConnectionError: Connection failed
        """
        # Note: AnkiConnect returns tags as part of notesInfo
        info = await self.notes_info([note_id])
        if info:
            return info[0].get("tags", [])
        return []

    async def delete_notes(self, note_ids: list[int]) -> None:
        """Delete notes from Anki.

        Args:
            note_ids: List of note IDs to delete

        Raises:
            AnkiConnectionError: Connection failed
            AnkiAPIError: Delete failed
        """
        await self.invoke("deleteNotes", {"notes": note_ids})


# Singleton instance
_client: AnkiClient | None = None


def get_anki_client() -> AnkiClient:
    """Get or create the singleton AnkiConnect client.

    Returns:
        Singleton AnkiClient instance
    """
    global _client
    if _client is None:
        _client = AnkiClient(settings.anki_connect_url, settings.anki_connect_version)
    return _client
