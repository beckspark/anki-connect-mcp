"""FastMCP server instance and main entry point."""

from fastmcp import FastMCP

# Create FastMCP application instance
app = FastMCP("anki-connect-mcp")

# Import tools and resources to register them with the MCP server
# This must come after app creation
from . import resources, tools  # noqa: E402, F401


def main() -> None:
    """Main entry point for the MCP server."""
    app.run()


if __name__ == "__main__":
    main()
