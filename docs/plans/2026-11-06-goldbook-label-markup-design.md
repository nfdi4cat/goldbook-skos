# Gold Book label markup: design

## Intent

Gold Book titles and label fields contain HTML markup, e.g. `<sup>13</sup>C-HMQC-NOESY`.
The import copies it verbatim into `skos:prefLabel` and `skos:altLabel`, and Skosmos shows the tags.
Labels must display without tags, keep superscripts and subscripts where plain text allows, and stay findable by the ASCII spelling users type (`13C`).

## Findings

Across the full dump (`goldbook-download/goldbook-terms.zip`), labels contain `<i>`, `<em>`, `<sub>`, `<sup>` and one `<span class="s">`, plus the entity `&#xF8;`.
Definitions contain no markup.
Sup/sub occur in titles and in synonym fields, sometimes nested (`MS<sup><i>n</i></sup>`).

Skosmos escapes labels everywhere except literal property values, so rendering markup would need a patched Skosmos and would still break text search and sorting.
voc4cat has no field for extra properties or `skos:hiddenLabel` (nfdi4cat/voc4cat-tool#398), and vocpub validation rejects extra triples.

## Goals

- No HTML tags or entities in any label the import writes.
- `<sup>`/`<sub>` content rendered as Unicode super-/subscript characters when every character has one: `¹³C-HMQC-NOESY`, `CO₂ laser`, `t₁`, `LC₅₀`, `MSⁿ`.
- The ASCII form of each converted label is searchable: added as an altLabel.

## Non-goals

- Rendering markup in Skosmos.
- Italics: Unicode has no italic form for text; `<i>`/`<em>` are dropped, keeping their content.
- Changes to definitions.

## Approaches

- **A. Plain text only**: strip tags. Search works; display loses all formatting.
- **B. Unicode prefLabel + ASCII altLabel** (chosen by David): keeps formatted display for isotopes, formulas and indices, and search on the ASCII spelling via `skos:altLabel`.
- **Rejected:** a separate HTML-label property (voc4cat/vocpub cannot carry it) and a Skosmos template patch (fork maintenance, raw HTML from data, does not fix search).

## Decisions

- A label is cleaned in two forms from the same parse: *display* (Unicode super/subscripts) and *ASCII* (sup/sub content inline). Both drop all other tags, keep their text, and unescape entities.
- A `<sup>`/`<sub>` segment is converted only if all its characters have a Unicode form; otherwise it stays inline in both forms (`βnuc`, `ET`, `pH0.5 or pH1/2`).
- The display form of the title is the prefLabel. Alternate labels are the display forms of all label fields, plus the ASCII form of every label whose ASCII form differs from its display form. The existing rules still apply: no duplicates, none equal to the prefLabel.
- *Claude's call:* parse with the standard library `html.parser.HTMLParser`, which handles nesting and entities, rather than regular expressions.
- *Claude's call:* tags outside `i`, `em`, `sup`, `sub`, `span` raise a `MappingError`, so new markup in a future dump is noticed instead of silently stripped.
- *Claude's call:* the cleaning function lives in `goldbook_import/mapping.py` next to `split_labels`; the `preferred_label` rule changes from `copy("title")` to a rule using it.

## Left to the builder

- The super-/subscript character tables (digits, signs, parentheses and the letters Unicode provides).
- Test fixtures for the label cases listed under Goals and Decisions.
