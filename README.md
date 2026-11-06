# Bringing IUPAC gold book to SKOS

Repository for the goldbook hacking section in [Ontologies4Chem](https://nfdi4chem.de/event/5th-ontologies4chem-workshop/) workshop on Nov 3-5th, 2026 in Limburg.

Sources of goldbooks data:
 * https://goldbook.iupac.org/pages/api/ (API access currently Cloudflare blocked)

## Running the import

The first import and every later update work the same way: the import rebuilds a complete xlsx from all IUPAC JSON files, and a pull request with that xlsx updates the vocabulary.

Requirements: [uv](https://docs.astral.sh/uv/), [just](https://github.com/casey/just), and for the local checks voc4cat-tool (`just setup`).

1. Start a branch from an up-to-date `main`:
   `git switch main`, `git pull`, `git switch -c <branch>`.
2. Build the xlsx: `just goldbook-import goldbook-download/gb1000`.
   The directory is relative to the repository root.
   This writes `inbox-excel-vocabs/goldbook.xlsx`; an invalid file, a duplicate id or a failing mapping rule stops the import and nothing is written.
3. Optional, to see the result locally: `just check convert docs` writes `outbox/goldbook.ttl` and the HTML documentation `outbox/goldbook/index.html`; `just clean` removes the generated files.
4. Commit only `inbox-excel-vocabs/goldbook.xlsx`, push the branch and open a pull request.
5. The CI converts the xlsx and replaces the branch's commit with a "CI: vocabulary update" commit that holds the turtle files in `vocabularies/goldbook/` and no xlsx.
   Do not push the local branch again afterwards; it still holds the xlsx commit.
6. GitHub holds the second CI run until a maintainer clicks "Approve and run" (see [README_TEMPLATE.md](README_TEMPLATE.md#why-a-second-workflow-run-has-to-be-approved)). Approve it, then merge.
7. After the merge: `git switch main`, `git pull`, `git branch -D <branch>`.

What an update changes:
- Concepts whose content is unchanged produce no diff; only changed and new concepts get a new `dcterms:modified` date.
- A concept missing from the new download counts as a deletion, which the CI rejects (`allow_delete = false` in `idranges.toml`).
- If nothing changed, the CI closes the pull request.
- New ids must lie in an `id_range` of the pull request's author in `idranges.toml` on `main`.

## Mapping of Gold Book JSON to SKOS

The import ([goldbook_import](goldbook_import/README.md)) maps each Gold Book term file to one `skos:Concept`.
The mapping is provisional; its source of truth is `CONCEPT_RULES` in [goldbook_import/mapping.py](goldbook_import/mapping.py).
All labels and definitions get the language tag `@en`.

| JSON element (`term.…`) | SKOS / RDF property | Comment |
|---|---|---|
| `id` | concept IRI, `dcterms:identifier` | IRI `https://w3id.org/goldbook/<id>` (provisional namespace); voc4cat derives the identifier from the IRI |
| `title` | `skos:prefLabel`, `skos:altLabel` | `<sup>`/`<sub>` become Unicode super-/subscripts where each of their characters has one (`<sup>13</sup>C` → `¹³C`), other tags are dropped and entities resolved; the ASCII form of a converted label (`13C`) is added as `skos:altLabel` so that search finds it; unknown tags stop the import |
| `longtitle` | (not mapped) | "IUPAC Gold Book - " + `title` |
| `doi` | `prov:hadPrimarySource` | as `https://doi.org/<doi>`; the DOI uses `code`, not `id` |
| `code` | (not mapped) | `id` with an optional letter prefix; used in DOIs and Gold Book URLs |
| `status` | `skos:editorialNote` | only for a status other than `current`: "Gold Book status: &lt;status&gt;" (temporary) |
| `synonym` | `skos:altLabel` | `<em>synonym(s)</em>: ` prefix removed, split on ", ", markup converted as for `title`; labels equal to the prefLabel and duplicates are dropped |
| `acronym` | `skos:altLabel` | as `synonym` |
| `initialism` | `skos:altLabel` | as `synonym` |
| `abbrev` | `skos:altLabel` | as `synonym` |
| `also defines` | (not mapped) | candidate for a later iteration |
| `mentioned` | (not mapped) | candidate for a later iteration |
| `antonym` | (not mapped) | candidate for a later iteration |
| `related` | (not mapped) | candidate for `skos:related` once voc4cat supports it |
| `index` | `skos:member` (of a `skos:Collection`) | one collection per value: `quantity` → "quantities" (`90001`), `unit` → "units" (`90002`), `constant` → "constants" (`90003`), `prefix` → "prefixes" (`90004`); an unknown value stops the import |
| `intro` | (not mapped) | |
| `definitions[].id` | (not mapped) | |
| `definitions[].text` | `skos:definition` | several definitions are numbered and joined into one text ("1. … 2. …"); HTML and LaTeX kept as is |
| `definitions[].links` | (not mapped) | basis for a planned broader-concept heuristic |
| `definitions[].sources` | (not mapped) | |
| `definitions[].notes` | (not mapped) | |
| `definitions[].contexts` | (not mapped) | |
| `definitions[].exams` | (not mapped) | |
| `definitions[].seealso` | (not mapped) | |
| `altoutputs` | (not mapped) | links to HTML, XML and plain-text versions of the term |
| `citation` | (not mapped) | |
| `license` | `dcterms:license` | constant `https://creativecommons.org/licenses/by-sa/4.0/`, as stated in the text |
| `collection` | (not mapped) | |
| `disclaimer` | (not mapped) | |
| `accessed` | (not mapped) | |
| (none) | `dcterms:rightsHolder` | constant "International Union of Pure and Applied Chemistry (IUPAC)" |

voc4cat tool adds further triples to every concept that do not come from the JSON: `skos:inScheme`, `skos:topConceptOf` (no hierarchy yet), `dcterms:provenance` and `rdfs:seeAlso` (links to the concept's file in this repository), and `dcterms:created`/`dcterms:modified` from the git history.

## Checking a IUPAC json download

`python -I scripts/check_json_files.py <directory>` checks a download without updating the vocabulary: every `*.json` file must be a Gold Book term record with the fields every record has, and `term.code` must match the file name (`<code>.json` or `goldbook_term_<code>.json`).
It lists each failing file with the reason and exits with 1 if any file fails.
The import validates the records itself, so the script is only needed to inspect a new download.
