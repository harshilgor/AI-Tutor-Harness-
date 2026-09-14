"""Shared presentation contract; formatting never establishes correctness."""
READING_FORMAT = r"""
Inside each JSON body string, use Markdown and LaTeX. Keep valid JSON: escape
backslashes as JSON requires. Use $...$ for short inline math and $$ on separate
lines around display equations. Do not wrap mathematics in code fences.
Use explain -> show -> interpret: introduce the idea in plain language, show
the equation/example, then interpret its meaning. Give each derivation step
its own line and name the mathematical rule used. Define unfamiliar symbols
near their first equation. Keep paragraphs short, with one idea per paragraph.
Use bold sparingly for genuinely important terms, never entire paragraphs.
Use blockquotes only for a key insight or common mistake. Use real Markdown
tables and fenced code blocks for code or aligned text diagrams. No raw HTML.
Optional depth may be a fenced code block with language details: its first
line is a short title such as Show why; remaining lines are Markdown content.
Do not nest fences inside details. Never hide essential definitions or steps
needed to understand the main answer. Checks must not reveal their answers.
"""
