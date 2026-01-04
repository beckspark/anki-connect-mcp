"""Configuration management using Pydantic settings."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # AnkiConnect API
    anki_connect_url: str = Field(
        default="http://localhost:8765", description="AnkiConnect API endpoint"
    )
    anki_connect_version: int = Field(default=6, description="AnkiConnect API version")

    # Default behavior
    default_deck: str = Field(default="Default", description="Default deck for new cards")
    generation_mode: Literal["auto", "hybrid"] = Field(
        default="hybrid",
        description="Card generation mode: auto (immediate) or hybrid (review first)",
    )

    # Validation
    validation_strictness: Literal["strict", "moderate", "lenient"] = Field(
        default="moderate", description="Validation strictness level"
    )
    max_answer_words: int = Field(default=50, description="Maximum words in answer before warning")

    # Content extraction
    extraction_timeout: int = Field(
        default=60, description="Timeout for PDF/ePub extraction in seconds"
    )

    # Database
    database_path: str = Field(
        default="~/.anki_mcp.db", description="Path to DuckDB database for history tracking"
    )


# Global settings instance
settings = Settings()
