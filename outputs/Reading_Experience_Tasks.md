# Reading experience task list

Scope: rich lesson rendering, mathematical explanations, contextual help, and reading comfort. Preserve the chat, attachments, sources, and canonical learner-state boundaries.

- [x] Shared Markdown/GFM and KaTeX renderer for lessons, material answers, and explanations.
- [x] Accessible math, local horizontal overflow, safe links, disabled raw HTML, and malformed-math fallback.
- [x] Restrained pastel accents for emphasized terms, equations, and key ideas.
- [x] Copyable code and text diagrams.
- [x] Explain → show → interpret prompts, nearby symbol definitions, and reasoned derivation steps.
- [x] Optional expandable detail and extra examples.
- [x] Equation and passage help: explain, simpler, example, symbols, and why.
- [x] Correct lesson/block anchoring across older chat turns.
- [x] Preserve reading position and restore focus when help closes.
- [x] Section outline for long lessons; position only, never mastery.
- [x] Saved text-size and spacing preferences, separate from Teaching Gear.
- [x] Compact source passages without fabricated claim-level citations.
- [x] Validate parsing, API contracts, responsive layout, preferences, and live reading interactions.

Existing plain-text lessons remain readable without guessing mathematical meaning. Newly generated lessons use the richer format.

## Implementation notes

- One shared `RichContent` renderer serves lessons, material answers, source passages, and sidecars. KaTeX emits HTML plus MathML; raw HTML and remote embedded images are disabled. Code and text diagrams preserve spacing and have copy controls.
- Sage emphasis, lavender equations, and amber callouts use dark text. Meaning is also expressed through semantic markup and wording, not color alone.
- `LessonReader` supplies saved size/spacing settings, section navigation, and expandable help actions. The outline tracks reading position, not learning progress.
- Equation help retains the original LaTeX as its source anchor and typesets the quote. Selection in older turns now carries its own lesson ID and block ID. Closing help restores focus without scrolling.
- Model instructions use explain → show → interpret, nearby symbol definitions, and reasoned derivation steps. Optional details use a dedicated safe Markdown convention. Actual explanation quality still depends on the model.
- Material source passages remain retrieval references, not fabricated claim-level verification badges. Historical plain-text lessons are preserved; new lessons use the richer format.

## Verification

- Full offline backend suite: 56 tests passed. A subsequent provider-format regression test was added; all 20 provider and explanation tests then passed.
- Renderer: 10 scenario checks passed, including malformed mathematics, unsafe markup/links, tables, diagrams, optional detail, and legacy prose.
- TypeScript, targeted ESLint, and full web build passed.
- Browser: correct fractions, subscripts, aligned equations, and MathML; saved settings survive reload; details expand; copy works; source LaTeX reaches the help flow.
- Live chat at 390 px: no document overflow and no math-rendering errors. The viewport override affects the active chat tab, rather than the background preview tab.
- Live explanation verification passed after tightening the model's JSON response contract: symbol definitions and numerical steps render correctly. Closing help restores section focus and preserves the exact document scroll position.

Preview: http://localhost:3000/reading-preview

Run the renderer checks from `web` with `node scripts/test-reading-renderer.cjs`.
