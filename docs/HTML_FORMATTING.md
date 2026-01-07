# HTML Formatting Guide for Anki Cards

This guide covers how to use HTML formatting in Anki flashcards created through the MCP server.

## Overview

Anki supports full HTML in card fields, allowing rich formatting including:
- Text styling (bold, italic, colors, etc.)
- Lists and tables
- Mathematical notation (subscripts, superscripts, MathJax)
- Images and links
- Custom layouts

The validation system automatically handles HTML by counting visible text length (excluding tags), so you don't need to worry about HTML markup affecting length limits.

## Direct HTML Usage

You can pass HTML directly as strings to any card creation function:

```python
# Basic formatting
create_basic_card(
    front="What is the chemical formula for <b>water</b>?",
    back="H<sub>2</sub>O",
    deck="Chemistry::Basics"
)

# Lists
create_basic_card(
    front="What are the three states of matter?",
    back="<ul><li>Solid</li><li>Liquid</li><li>Gas</li></ul>",
    deck="Physics"
)

# Colors and styling
create_basic_card(
    front="What color is a stop sign?",
    back='<span style="color: red; font-weight: bold;">Red</span>',
    deck="Driving"
)

# Cloze with HTML
create_cloze_card(
    text="Water has the formula {{c1::H<sub>2</sub>O}}.",
    deck="Chemistry"
)
```

## Using Helper Functions

The `anki_connect_mcp.formatting` module provides convenient helpers for common patterns:

```python
from anki_connect_mcp.formatting import (
    bold, italic, underline, color, highlight,
    code, unordered_list, ordered_list, table,
    subscript, superscript, line_break,
    mathjax_inline, mathjax_block
)

# Text formatting
back = f"{bold('Important:')} This is a key concept."
# Result: "<b>Important:</b> This is a key concept."

# Chemical formulas
formula = f"H{subscript('2')}O"
# Result: "H<sub>2</sub>O"

# Math notation
equation = f"x{superscript('2')} + y{superscript('2')} = z{superscript('2')}"
# Result: "x<sup>2</sup> + y<sup>2</sup> = z<sup>2</sup>"

# Lists
steps = unordered_list(["First step", "Second step", "Third step"])
# Result: "<ul><li>First step</li><li>Second step</li><li>Third step</li></ul>"

# Colors
warning = color("Danger!", "red")
# Result: '<span style="color: red;">Danger!</span>'

# Highlighting
important = highlight("This is crucial", "yellow")
# Result: '<span style="background-color: yellow;">This is crucial</span>'

# Code
code_example = code("print('hello')")
# Result: "<code>print('hello')</code>"
```

## Common Formatting Patterns

### 1. Scientific Notation

```python
# Chemistry
create_basic_card(
    front="What is the molecular formula for glucose?",
    back="C<sub>6</sub>H<sub>12</sub>O<sub>6</sub>",
    deck="Chemistry::Organic"
)

# Physics
create_basic_card(
    front="What is Einstein's mass-energy equation?",
    back="E = mc<sup>2</sup>",
    deck="Physics::Relativity"
)
```

### 2. Structured Lists

```python
# Ordered lists for steps/procedures
create_basic_card(
    front="What are the steps of the scientific method?",
    back="""
    <ol>
        <li>Ask a question</li>
        <li>Do background research</li>
        <li>Construct a hypothesis</li>
        <li>Test with an experiment</li>
        <li>Analyze data</li>
        <li>Draw conclusions</li>
    </ol>
    """,
    deck="Science::Method"
)

# Unordered lists for categories
create_basic_card(
    front="What are the main food groups?",
    back="""
    <ul>
        <li>Fruits and vegetables</li>
        <li>Proteins</li>
        <li>Grains</li>
        <li>Dairy</li>
    </ul>
    """,
    deck="Health::Nutrition"
)
```

### 3. Color-Coded Information

```python
# Use colors to emphasize key information
create_basic_card(
    front="What are the oxidation states of nitrogen in NO<sub>2</sub>?",
    back='<span style="color: blue;">+4</span> oxidation state',
    deck="Chemistry::Oxidation"
)

# Highlighting for warnings or critical info
create_basic_card(
    front="What should you never mix with bleach?",
    back='<span style="background-color: yellow; color: red; font-weight: bold;">Ammonia</span> - creates toxic chloramine gas',
    deck="Safety::Household"
)
```

### 4. Tables

```python
# Comparison tables
create_basic_card(
    front="Compare DNA and RNA",
    back="""
    <table border="1">
        <thead>
            <tr>
                <th>Feature</th>
                <th>DNA</th>
                <th>RNA</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Sugar</td>
                <td>Deoxyribose</td>
                <td>Ribose</td>
            </tr>
            <tr>
                <td>Strands</td>
                <td>Double</td>
                <td>Single</td>
            </tr>
            <tr>
                <td>Bases</td>
                <td>A, T, G, C</td>
                <td>A, U, G, C</td>
            </tr>
        </tbody>
    </table>
    """,
    deck="Biology::Molecular"
)
```

### 5. Mixed Formatting

```python
# Combine multiple formatting techniques
create_basic_card(
    front="What is the <i>Krebs cycle</i> also known as?",
    back="""
    Also called:<br>
    <ul>
        <li><b>Citric acid cycle</b></li>
        <li><b>TCA cycle</b> (tricarboxylic acid)</li>
    </ul>
    <br>
    <i>Named after Hans Krebs (1937)</i>
    """,
    deck="Biology::Metabolism"
)
```

## MathJax Support

Anki supports MathJax for advanced mathematical notation:

```python
from anki_connect_mcp.formatting import mathjax_inline, mathjax_block

# Inline math
create_basic_card(
    front="What is the quadratic formula?",
    back=mathjax_inline(r"x = \frac{-b \pm \sqrt{b^2-4ac}}{2a}"),
    deck="Math::Algebra"
)

# Display (block) math
create_basic_card(
    front="What is the integral of e^(-x^2)?",
    back=mathjax_block(r"\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}"),
    deck="Math::Calculus"
)

# In cloze cards
create_cloze_card(
    text=f"The derivative of sin(x) is {mathjax_inline('{{c1::cos(x)}}')}"
    deck="Math::Calculus"
)
```

## Card Template CSS (Advanced)

While the MCP API handles field content (HTML in fields), you can also customize card templates directly in Anki for deck-wide styling:

### Accessing Template Editor

1. Open Anki
2. Click on a deck
3. Click the gear icon → "Manage Note Types"
4. Select your note type → "Cards"
5. Edit the "Styling" section (CSS)

### Common CSS Customizations

```css
/* Centered, larger text */
.card {
    font-family: Arial, sans-serif;
    font-size: 20px;
    text-align: center;
    color: #333;
    background-color: #fafafa;
}

/* Highlight answer text */
.back {
    color: #0066cc;
    font-weight: bold;
}

/* Style specific fields */
.front {
    font-size: 24px;
}

/* Platform-specific styling */
.mobile .card {
    font-size: 18px;
}

.win .card {
    font-family: "Segoe UI", sans-serif;
}

/* Night mode support */
.nightMode .card {
    background-color: #2b2b2b;
    color: #e0e0e0;
}

/* Custom classes you can use in fields */
.important {
    background-color: yellow;
    padding: 5px;
}

.definition {
    font-style: italic;
    border-left: 3px solid #0066cc;
    padding-left: 10px;
}
```

### Using Custom CSS Classes in Fields

Once you define classes in the template styling, use them in field HTML:

```python
create_basic_card(
    front="What is photosynthesis?",
    back='<div class="definition">The process by which plants convert light energy into chemical energy</div>',
    deck="Biology"
)
```

## Best Practices

### DO:
- ✅ Use HTML for structure (lists, tables, subscripts/superscripts)
- ✅ Use inline styles for colors and highlights when needed
- ✅ Keep formatting minimal and purposeful
- ✅ Test cards in Anki to see how they render
- ✅ Use semantic HTML (`<em>` for emphasis, `<strong>` for importance)
- ✅ Escape user-provided text with `html.escape()` if programmatically generating cards

### DON'T:
- ❌ Over-format cards - simple is better for retention
- ❌ Use complex layouts that distract from content
- ❌ Rely on very small font sizes or subtle colors (mobile visibility)
- ❌ Forget to test on mobile if you study there
- ❌ Use JavaScript (limited support, not recommended)

## Validation with HTML

The validation system automatically strips HTML when checking:
- **Character limits:** Only visible text counts
- **Word counts:** HTML tags are excluded
- **Length checks:** Measures actual content, not markup

```python
# This passes validation even though the raw string is longer
create_basic_card(
    front="<b>Short</b>",  # Counts as 5 chars, not 11
    back="<ul><li>A</li><li>B</li></ul>",  # Counts as 2 words
    deck="Test"
)
```

## Helper Function Reference

| Function | Description | Example |
|----------|-------------|---------|
| `bold(text)` | Bold text | `bold("important")` → `<b>important</b>` |
| `italic(text)` | Italic text | `italic("emphasis")` → `<i>emphasis</i>` |
| `underline(text)` | Underlined text | `underline("key")` → `<u>key</u>` |
| `color(text, color_value)` | Colored text | `color("red", "red")` → `<span style="color: red;">red</span>` |
| `highlight(text, bg_color)` | Highlighted text | `highlight("key", "yellow")` → with yellow background |
| `code(text, inline=True)` | Code formatting | `code("x=1")` → `<code>x=1</code>` |
| `unordered_list(items)` | Bullet list | `unordered_list(["A", "B"])` → `<ul><li>A</li>...</ul>` |
| `ordered_list(items)` | Numbered list | `ordered_list(["A", "B"])` → `<ol><li>A</li>...</ol>` |
| `table(rows, headers)` | HTML table | See examples above |
| `subscript(text)` | Subscript | `subscript("2")` → `<sub>2</sub>` |
| `superscript(text)` | Superscript | `superscript("2")` → `<sup>2</sup>` |
| `line_break(count)` | Line breaks | `line_break(2)` → `<br><br>` |
| `div(content, class, style)` | Div wrapper | `div("text", css_class="important")` |
| `mathjax_inline(latex)` | Inline math | `mathjax_inline("x^2")` → `\\(x^2\\)` |
| `mathjax_block(latex)` | Display math | `mathjax_block("x^2")` → `\\[x^2\\]` |
| `strip_html(text)` | Remove HTML tags | `strip_html("<b>hi</b>")` → `"hi"` |
| `get_text_length(text)` | Length without HTML | `get_text_length("<b>hi</b>")` → `2` |

## Examples by Subject

### Chemistry

```python
# Formulas with subscripts/superscripts
create_basic_card(
    front="What is the formula for sulfuric acid?",
    back="H<sub>2</sub>SO<sub>4</sub>",
    deck="Chemistry::Acids"
)

# Balanced equations
create_basic_card(
    front="Balance this equation: H<sub>2</sub> + O<sub>2</sub> → H<sub>2</sub>O",
    back="2H<sub>2</sub> + O<sub>2</sub> → 2H<sub>2</sub>O",
    deck="Chemistry::Balancing"
)
```

### Mathematics

```python
# Fractions and equations
create_basic_card(
    front="Simplify: (x<sup>2</sup> - 4)/(x - 2)",
    back="x + 2",
    deck="Math::Algebra"
)

# With MathJax for complex notation
create_cloze_card(
    text=f"{mathjax_inline(r'\lim_{x \to 0} \frac{\sin x}{x}')} = {{c1::1}}",
    deck="Math::Limits"
)
```

### Biology

```python
# Italicized species names
create_basic_card(
    front="What is the scientific name for humans?",
    back="<i>Homo sapiens</i>",
    deck="Biology::Taxonomy"
)

# Processes with lists
create_basic_card(
    front="What are the stages of mitosis?",
    back="<ol><li>Prophase</li><li>Metaphase</li><li>Anaphase</li><li>Telophase</li></ol>",
    deck="Biology::CellDivision"
)
```

### Programming

```python
# Code examples
create_basic_card(
    front="How do you define a function in Python?",
    back='<code>def function_name(parameters):<br>&nbsp;&nbsp;&nbsp;&nbsp;# function body</code>',
    deck="Programming::Python"
)

# Syntax highlighting (manual)
create_basic_card(
    front="What is the correct if statement syntax?",
    back='<code><span style="color: purple;">if</span> condition:<br>&nbsp;&nbsp;&nbsp;&nbsp;statement</code>',
    deck="Programming::Syntax"
)
```

## Troubleshooting

### HTML Not Rendering

- **Check Anki app:** View the card in Anki to confirm it's rendering correctly
- **Check quotes:** Use straight quotes (`"`) not smart/curly quotes (`"`)
- **Check tag closure:** Ensure all tags are properly closed (`<b>text</b>`)

### Layout Issues

- **Mobile display:** Test on mobile if you study there
- **Template conflicts:** Card template CSS might override inline styles
- **Table widths:** Tables might overflow on small screens

### Special Characters

- **Use HTML entities:** `&lt;` for <, `&gt;` for >, `&amp;` for &
- **Or use `html.escape()`:** The helper functions do this automatically

## Further Reading

- [Anki Manual - Styling & HTML](https://docs.ankiweb.net/templates/styling.html)
- [Anki Manual - Card Templates](https://docs.ankiweb.net/templates/intro.html)
- [Anki Manual - Editing](https://docs.ankiweb.net/editing.html)
- [MathJax Documentation](https://docs.mathjax.org/)
- [HTML Reference](https://developer.mozilla.org/en-US/docs/Web/HTML)
- [CSS Reference](https://developer.mozilla.org/en-US/docs/Web/CSS)
