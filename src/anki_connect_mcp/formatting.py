"""HTML formatting utilities for Anki flashcards.

Anki supports full HTML in card fields. These utilities provide convenient
helpers for common formatting patterns while allowing direct HTML when needed.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from pygments import highlight as _pygments_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound


def bold(text: str) -> str:
    """Wrap text in bold formatting.

    Args:
        text: Text to make bold

    Returns:
        HTML-formatted bold text

    Example:
        >>> bold("important")
        '<b>important</b>'
    """
    return f"<b>{html.escape(text)}</b>"


def italic(text: str) -> str:
    """Wrap text in italic formatting.

    Args:
        text: Text to italicize

    Returns:
        HTML-formatted italic text

    Example:
        >>> italic("emphasis")
        '<i>emphasis</i>'
    """
    return f"<i>{html.escape(text)}</i>"


def underline(text: str) -> str:
    """Wrap text in underline formatting.

    Args:
        text: Text to underline

    Returns:
        HTML-formatted underlined text

    Example:
        >>> underline("key term")
        '<u>key term</u>'
    """
    return f"<u>{html.escape(text)}</u>"


def color(text: str, color_value: str) -> str:
    """Apply color to text.

    Args:
        text: Text to color
        color_value: CSS color value (name, hex, rgb, etc.)

    Returns:
        HTML-formatted colored text

    Example:
        >>> color("warning", "red")
        '<span style="color: red;">warning</span>'
        >>> color("note", "#4a90e2")
        '<span style="color: #4a90e2;">note</span>'
    """
    return f'<span style="color: {html.escape(color_value)};">{html.escape(text)}</span>'


def highlight(text: str, bg_color: str = "yellow") -> str:
    """Highlight text with background color.

    Args:
        text: Text to highlight
        bg_color: Background color (default: yellow)

    Returns:
        HTML-formatted highlighted text

    Example:
        >>> highlight("key concept")
        '<span style="background-color: yellow;">key concept</span>'
    """
    return f'<span style="background-color: {html.escape(bg_color)};">{html.escape(text)}</span>'


def code(text: str, inline: bool = True) -> str:
    """Format text as code.

    Args:
        text: Code to format
        inline: If True, use inline code style; if False, use code block

    Returns:
        HTML-formatted code

    Example:
        >>> code("print('hello')")
        '<code>print(&#x27;hello&#x27;)</code>'
        >>> code("def foo():\\n    pass", inline=False)
        '<pre><code>def foo():\n    pass</code></pre>'
    """
    escaped = html.escape(text)
    if inline:
        return f"<code>{escaped}</code>"
    return f"<pre><code>{escaped}</code></pre>"


def unordered_list(items: list[str]) -> str:
    """Create an unordered (bullet) list.

    Args:
        items: List items

    Returns:
        HTML unordered list

    Example:
        >>> unordered_list(["First", "Second", "Third"])
        '<ul><li>First</li><li>Second</li><li>Third</li></ul>'
    """
    list_items = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    return f"<ul>{list_items}</ul>"


def ordered_list(items: list[str]) -> str:
    """Create an ordered (numbered) list.

    Args:
        items: List items

    Returns:
        HTML ordered list

    Example:
        >>> ordered_list(["First step", "Second step"])
        '<ol><li>First step</li><li>Second step</li></ol>'
    """
    list_items = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    return f"<ol>{list_items}</ol>"


def table(rows: list[list[str]], headers: list[str] | None = None) -> str:
    """Create an HTML table.

    Args:
        rows: List of rows, where each row is a list of cell values
        headers: Optional header row

    Returns:
        HTML table

    Example:
        >>> table([["A", "1"], ["B", "2"]], headers=["Letter", "Number"])
        '<table><thead><tr><th>Letter</th><th>Number</th></tr></thead><tbody><tr><td>A</td><td>1</td></tr><tr><td>B</td><td>2</td></tr></tbody></table>'
    """
    html_parts = ["<table>"]

    if headers:
        header_cells = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
        html_parts.append(f"<thead><tr>{header_cells}</tr></thead>")

    html_parts.append("<tbody>")
    for row in rows:
        cells = "".join(f"<td>{html.escape(cell)}</td>" for cell in row)
        html_parts.append(f"<tr>{cells}</tr>")
    html_parts.append("</tbody></table>")

    return "".join(html_parts)


def line_break(count: int = 1) -> str:
    """Insert line break(s).

    Args:
        count: Number of line breaks (default: 1)

    Returns:
        HTML line break(s)

    Example:
        >>> line_break()
        '<br>'
        >>> line_break(2)
        '<br><br>'
    """
    return "<br>" * count


def subscript(text: str) -> str:
    """Format text as subscript.

    Args:
        text: Text to subscript

    Returns:
        HTML subscript

    Example:
        >>> subscript("2")
        '<sub>2</sub>'
        >>> f"H{subscript('2')}O"
        'H<sub>2</sub>O'
    """
    return f"<sub>{html.escape(text)}</sub>"


def superscript(text: str) -> str:
    """Format text as superscript.

    Args:
        text: Text to superscript

    Returns:
        HTML superscript

    Example:
        >>> superscript("2")
        '<sup>2</sup>'
        >>> f"x{superscript('2')}"
        'x<sup>2</sup>'
    """
    return f"<sup>{html.escape(text)}</sup>"


def div(content: str, css_class: str | None = None, style: str | None = None) -> str:
    """Wrap content in a div with optional class or inline styles.

    Args:
        content: Content to wrap (can include HTML)
        css_class: Optional CSS class name
        style: Optional inline CSS styles

    Returns:
        HTML div element

    Example:
        >>> div("content", css_class="important")
        '<div class="important">content</div>'
        >>> div("centered", style="text-align: center;")
        '<div style="text-align: center;">centered</div>'
    """
    attrs = []
    if css_class:
        attrs.append(f'class="{html.escape(css_class)}"')
    if style:
        attrs.append(f'style="{html.escape(style)}"')

    attr_str = " " + " ".join(attrs) if attrs else ""
    return f"<div{attr_str}>{content}</div>"


def strip_html(text: str) -> str:
    """Remove all HTML tags from text.

    Useful for counting actual text length or extracting plain text.

    Args:
        text: Text potentially containing HTML

    Returns:
        Plain text with HTML tags removed

    Example:
        >>> strip_html("<b>Hello</b> <i>world</i>")
        'Hello world'
    """
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = html.unescape(text)
    return text


def get_text_length(text: str) -> int:
    """Get the length of text excluding HTML tags.

    Useful for validation that should count visible characters only.

    Args:
        text: Text potentially containing HTML

    Returns:
        Character count excluding HTML markup

    Example:
        >>> get_text_length("<b>Hello</b>")
        5
        >>> get_text_length("Plain text")
        10
    """
    return len(strip_html(text))


def mathjax_inline(latex: str) -> str:
    """Format LaTeX math for inline rendering with MathJax.

    Args:
        latex: LaTeX math expression (without delimiters)

    Returns:
        MathJax-formatted inline math

    Example:
        >>> mathjax_inline("x^2 + y^2 = z^2")
        '\\\\(x^2 + y^2 = z^2\\\\)'
    """
    return f"\\({latex}\\)"


def mathjax_block(latex: str) -> str:
    """Format LaTeX math for block (display) rendering with MathJax.

    Args:
        latex: LaTeX math expression (without delimiters)

    Returns:
        MathJax-formatted display math

    Example:
        >>> mathjax_block("\\\\int_0^\\\\infty e^{-x^2} dx = \\\\frac{\\\\sqrt{\\\\pi}}{2}")
        '\\\\[\\\\int_0^\\\\infty e^{-x^2} dx = \\\\frac{\\\\sqrt{\\\\pi}}{2}\\\\]'
    """
    return f"\\[{latex}\\]"


# ---------------------------------------------------------------------------
# Syntax highlighting (matches "Syntax Highlighter fixed by Shige" addon)
# ---------------------------------------------------------------------------

# Dark themes list matching Shige's themes.py
_DARK_THEMES = frozenset(
    [
        "monokai",
        "github-dark",
        "lightbulb",
        "rrt",
        "zenburn",
        "nord",
        "material",
        "one-dark",
        "dracula",
        "nord-darker",
        "gruvbox-dark",
        "stata-dark",
        "paraiso-dark",
        "coffee",
        "solarized-dark",
        "native",
        "inkpot",
        "fruity",
        "vim",
    ]
)

_shige_config: dict[str, object] | None = None


def _get_shige_config() -> dict[str, object]:
    """Read Shige addon config, falling back to sensible defaults."""
    global _shige_config
    if _shige_config is not None:
        return _shige_config

    meta_path = Path.home() / ".local/share/Anki2/addons21/272582198/meta.json"
    defaults: dict[str, object] = {
        "style": "monokai",
        "linenos": False,
        "centerfragments": True,
        "cssclasses": False,
        "font-size": 15,
    }

    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            cfg = meta.get("config", {})
            defaults["style"] = cfg.get("style", defaults["style"])
            defaults["linenos"] = cfg.get("linenos", defaults["linenos"])
            defaults["centerfragments"] = cfg.get("centerfragments", defaults["centerfragments"])
            defaults["cssclasses"] = cfg.get("cssclasses", defaults["cssclasses"])
            defaults["font-size"] = cfg.get("font-size", defaults["font-size"])
        except (json.JSONDecodeError, OSError):
            pass  # keep defaults

    _shige_config = defaults
    return _shige_config


def _escape_anki_syntax(text: str) -> str:
    """Escape Anki template syntax in highlighted code output.

    Prevents Anki's template engine from interpreting ``{{``, ``}}``, and
    ``::`` sequences inside code blocks.
    """
    text = text.replace("{{", "{<!---->{")
    text = text.replace("}}", "}<!---->}")
    text = text.replace("::", ":<!---->:")
    return text


def highlight_code(code: str, language: str = "python") -> str:
    """Syntax-highlight a code string, producing output identical to the Shige addon.

    Uses Pygments with inline styles and wraps the result in the same
    ``<center><table>`` structure that the Shige addon produces.

    Args:
        code: Raw source code to highlight.
        language: Pygments lexer name (e.g., "python", "sql", "javascript").

    Returns:
        HTML string with inline-styled syntax highlighting ready for Anki.
    """
    config = _get_shige_config()
    style_name = str(config.get("style", "monokai"))
    linenos = config.get("linenos", False)
    centerfragments = config.get("centerfragments", True)
    noclasses = not config.get("cssclasses", False)

    try:
        lexer = get_lexer_by_name(language, stripall=True)
    except ClassNotFound:
        lexer = get_lexer_by_name("text", stripall=True)

    formatter = HtmlFormatter(
        linenos="inline" if linenos else False,
        noclasses=noclasses,
        style=style_name,
        cssstyles="padding-left:8px; padding-right:8px;",
    )

    highlighted = _pygments_highlight(code, lexer, formatter)

    # Determine text color based on theme darkness (matches Shige's logic)
    if noclasses:
        color_style = "color:#ccc;" if style_name.lower() in _DARK_THEMES else "color:#222;"
    else:
        color_style = ""

    font_size = config.get("font-size", 15)
    table_style = f'style="{color_style} font-size: {font_size}px;"'

    if centerfragments:
        result = (
            f"<center><table {table_style}><tbody><tr><td>"
            f"{highlighted}"
            f"</td></tr></tbody></table></center><br>"
        )
    else:
        result = f"<table {table_style}><tbody><tr><td>{highlighted}</td></tr></tbody></table>"

    return _escape_anki_syntax(result)


# Regex for <pre><code class="language-X">...</code></pre> blocks
_CODE_BLOCK_RE = re.compile(
    r"<pre><code\s+class=\"language-(\w+)\">(.*?)</code></pre>",
    re.DOTALL,
)


def highlight_code_blocks(html_content: str) -> str:
    """Find and highlight all fenced code blocks in HTML content.

    Matches ``<pre><code class="language-X">...</code></pre>`` patterns
    (the standard way to mark code blocks in card HTML) and replaces them
    with Pygments-highlighted output matching the Shige addon format.

    Plain ``<code>`` tags (inline code) are left unchanged.

    Args:
        html_content: Card field HTML that may contain code blocks.

    Returns:
        HTML with code blocks replaced by syntax-highlighted versions.
        Returns the input unchanged if no code blocks are found.
    """

    def _replace_match(m: re.Match[str]) -> str:
        language = m.group(1)
        code_text = html.unescape(m.group(2))
        return highlight_code(code_text, language)

    return _CODE_BLOCK_RE.sub(_replace_match, html_content)


# Convenience exports for common formatting patterns
__all__ = [
    "bold",
    "italic",
    "underline",
    "color",
    "highlight",
    "code",
    "unordered_list",
    "ordered_list",
    "table",
    "line_break",
    "subscript",
    "superscript",
    "div",
    "strip_html",
    "get_text_length",
    "mathjax_inline",
    "mathjax_block",
    "highlight_code",
    "highlight_code_blocks",
]
