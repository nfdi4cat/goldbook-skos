# Gold Book JSON import: design

## Intent

Publish the IUPAC Gold Book as a SKOS vocabulary maintained with voc4cat in this repository.
IUPAC stays the master of the content for the foreseeable future, so the vocabulary is regenerated from the Gold Book JSON download by a repeatable import.
The first version is a first shot to get feedback from IUPAC colleagues; IRIs, metadata and mapping are provisional and will change as we iterate.
How Gold Book fields map to SKOS is not settled: we expect to iterate on it, including transformations that need the whole record and knowledge of all other records (for example deriving a broader concept from a term that is both linked in the definition and placed at a characteristic position in its text).

## Goals

- A repeatable import from a directory of Gold Book term JSON files to a voc4cat v1 xlsx file.
- The resulting xlsx goes through the unchanged voc4cat pipeline of this repository (PR checks, conversion, provenance, documentation, publishing).
- The mapping from Gold Book fields to voc4cat model fields lives in one place and is easy to change; a mapping rule may call any Python function.
- Every run validates the complete download against a Pydantic model of a Gold Book record and stops with a clear report on records that do not fit.
- The concept identifier is the Gold Book `id` (five digits), not `code`.

## Non-goals

- Changes to voc4cat-tool. The import uses voc4cat-tool as a library at the version this repository's CI pins.
- Editing the generated vocabulary by hand. It is read-only output for now; the pipeline features stay available so that this can change later.
- Downloading from the Gold Book API (currently blocked by Cloudflare). The import reads an existing download.
- A general JSON import for voc4cat. The design is specific to the Gold Book.
- A mapping library (glom, linkml-map, py-automapper) or RML. Rejected in favour of a plain mapping table; see Approaches.

## Anti-goals

- A mapping spread across the import code, so that trying a different SKOS representation means editing control flow.
- An import that silently skips or truncates records it does not understand.

## Constraints

- voc4cat's v1 models (`voc4cat.models_v1`) define what can be expressed: one definition per concept and language, no column for `skos:related` or `skos:note`. SKOS elements missing from these models, such as `skos:related`, may be added in a later step; until then the mapping cannot produce them.
- `excel_to_rdf_v1` and the CI pipeline consume an xlsx in `inbox-excel-vocabs/`. The vocabulary name in `idranges.toml` must equal the xlsx file stem.
- The CI checks that IDs used in a PR lie in an `id_range` of `idranges.toml` assigned to the PR author.
- `checks.allow_delete = false` makes a PR fail that removes a concept. A term that disappears from the Gold Book will need an explicit decision then.

## Approaches

**A. Import writes an xlsx; the existing pipeline converts it (chosen).**
A script validates the JSON with a Pydantic model, applies the mapping table to build `ConceptV1` and `MappingV1` rows, and writes `inbox-excel-vocabs/goldbook.xlsx` with voc4cat's `export_vocabulary_v1`.
A PR containing that file runs the full CI as for any xlsx submission.
No voc4cat-tool change; everything we iterate on stays in this repository.
Limitation: only what the `ConceptV1`/`MappingV1` columns hold reaches the vocabulary. Approach B shares this limit.

**B. Expose the model-to-RDF step of voc4cat-tool.**
Factor the part of `excel_to_rdf_v1` after the xlsx reading into a public function and call it from the import, writing turtle directly.
Cleaner data path, but needs a voc4cat-tool release and a second CI entry path, because the CI starts from an xlsx in the inbox.

**C. Generic JSON import in voc4cat-tool with a pluggable mapping module.**
Most reusable, but designs a plugin interface before the Gold Book mapping is known.

David chose A, because it keeps the whole pipeline without touching voc4cat-tool.

For the mapping, plain Pydantic (aliases on the target, or `model_validate(..., from_attributes=True)` from a view class), glom, py-automapper, linkml-map and RML were considered.
Most rules are functions of the whole record plus an index over all records, so a declarative path library adds little.
linkml-map would require LinkML schemas for both sides; RML bypasses the voc4cat models.
David chose a plain mapping table.

## Design

### Components

1. **Gold Book record model** (Pydantic). Models a term file: the top-level `term` object with its fields (`id`, `title`, `code`, `doi`, `status`, `definitions` with `text`, `links`, `sources`, `notes`, ...; the optional label fields `synonym`, `acronym`, `initialism`, `abbrev`, `also defines`, `mentioned`, `antonym`, `related`, `index`, `intro`; the licence and citation fields).
   Field names with spaces are reached through aliases.
   Validation is strict enough that an HTML error page, a truncated file or a changed schema fails loudly.
2. **Term index.** Built once from all validated records; gives lookups needed by mapping rules, at least `code` → record and `id` → record.
   Mapping rules receive it read-only.
3. **Mapping table** (one module). For each target model (`ConceptV1`, `MappingV1`) a table from target field name to a rule.
   A rule is a function `(record, index) -> value`.
   Small helpers build common rules (copy a field, constant value), so simple entries stay one line.
   Fields absent from the table keep the model default.
   Transformation functions (stripping `<em>synonym</em>: `, resolving `code` links to concept IRIs, broader-concept heuristics) are ordinary functions in or next to this module.
4. **Import script.** Reads the JSON directory, validates every file, builds the index, applies the mapping to every record, builds the concept scheme from `idranges.toml` (voc4cat's `config_to_concept_scheme_v1`), and writes the xlsx with `export_vocabulary_v1`.
   It reports all invalid records before failing, not only the first.

### Initial mapping

A starting point to iterate on, not a commitment. Items marked "Claude's call" were not discussed with David.

| `ConceptV1` field | Source | Note |
|---|---|---|
| `concept_iri` | `id` | `<permanent_iri_part><id>` from `idranges.toml` |
| `language_code` | constant `en` | |
| `preferred_label` | `title` | |
| `definition` | `definitions[].text` | one definition: its text. Several: numbered and joined into one text (Claude's call; voc4cat allows one per language) |
| `alternate_labels` | `synonym`, `acronym`, `initialism`, `abbrev` | `<em>…</em>: ` prefix removed (Claude's call which fields count as labels) |
| `source_vocab_iri` | `doi` | as `https://doi.org/<doi>` (Claude's call) |
| `source_vocab_license` | constant | `https://creativecommons.org/licenses/by-sa/4.0/`, as stated in `license` |
| `source_vocab_rights_holder` | constant | IUPAC |
| `parent_iris` | none yet | broader-concept heuristic from `links` is a later iteration |
| `editorial_note` | `status` | for a status other than `current` (e.g. `onhold`): `Gold Book status: <status>`; temporary, until a better representation is chosen |

HTML (`<i>`, `<sub>`, `<sup>`, `<span>`) and LaTeX math (`\(...\)`) inside titles and definitions are kept as they are in the first iteration; how to render them is a later mapping iteration (Claude's call).

Not mapped initially (no matching column or not yet decided): `also defines`, `mentioned`, `antonym`, `related`, `index`, `intro`, definition `sources`, `notes`, `contexts`, `exams`, `seealso`.
No `MappingV1` rows initially; the table for it exists so that external mappings can be added.

### Repository setup

- `idranges.toml`: replace `vocab_example` by a `goldbook` vocabulary with `id_length = 5`.
  - IRIs, provisional (the namespace is not decided): `vocabulary_iri` and `permanent_iri_part` `https://w3id.org/goldbook/`, so a concept IRI is `https://w3id.org/goldbook/01082`; prefix `goldbook`.
  - Creator, publisher and custodian are provisional and to be confirmed with the IUPAC colleagues (Claude's call: publisher IUPAC with its ROR).
  - One `id_range` assigns all existing Gold Book ids to `dalito` (David), who opens the import PRs; the CI checks IDs against the PR author. Ranges for new ids are assigned later as needed.
- Delete `vocabularies/vocab_example/`.
- These changes are merged to `main` in their own PR before the first import PR, because the CI reads `idranges.toml` from `main`.
- `scripts/check_json_files.py` stays as it is; the record model covers its checks for the import itself.

### Running it

- The first runs use the 1000-term download (`goldbook-download/gb1000`) to keep the pipeline runtime short; the full download follows once the mapping has had feedback.
- A `just` recipe runs the import, so a local run is `just goldbook-import <json-dir>` followed by the existing `just all` to see the pipeline result.
- The script declares its dependencies (voc4cat-tool at the CI-pinned version, pydantic) as PEP 723 inline metadata and runs with `uv run`, matching the repository's use of uv (Claude's call).
- An update from IUPAC: new download, run the import locally, open a PR with the xlsx.
- Later option, not part of the first shot: a `workflow_dispatch` GitHub workflow that fetches the JSON from where it is stored, runs the import and opens the PR. The `id_range` would then have to name the account that workflow acts as.

### Testing

TDD for the record model, the index, every transformation function and the import script (end to end on a small set of real Gold Book files, comparing the generated rows).
Tests run with pytest through uv.

## Left to the builder

- Module and file layout under `scripts/` (or a small package), names of helpers.
- Exact Pydantic strictness settings, as long as malformed or unexpected records fail with a readable message.
- How the import reports progress and errors.
- Which real Gold Book files serve as test fixtures.
