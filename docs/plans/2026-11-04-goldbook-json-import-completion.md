# Gold Book JSON Import - Completion

**PR:** Merged locally
**Branch:** goldbook-json-import
**Date:** 2026-11-04 to 2026-11-04
**Sessions:** afdb26c4-1cd6-48f4-aa5a-60f7bc39390d

## Summary

- Configured the `goldbook` vocabulary in `idranges.toml` (provisional IRIs under `https://w3id.org/goldbook/`, 5-digit ids) and removed the template's example vocabulary.
- Added a Pydantic model of Gold Book term files that rejects unknown keys and reports every invalid file.
- Added the mapping table from Gold Book records to voc4cat `ConceptV1` rows, with rules that receive the record and an index of all records.
- Added the import command that writes `inbox-excel-vocabs/goldbook.xlsx` for the unchanged voc4cat pipeline, plus `just goldbook-import` and `just test-import`.

## Key Changes

- `idranges.toml` (modified)
- `vocabularies/vocab_example/` (removed)
- `goldbook_import/goldbook_model.py` (new)
- `goldbook_import/mapping.py` (new)
- `goldbook_import/import_goldbook.py` (new)
- `goldbook_import/tests/` (new)
- `goldbook_import/pyproject.toml`, `goldbook_import/uv.lock` (new)
- `justfile` (modified)

## Related Documents

- Design: docs/plans/2026-11-04-goldbook-json-import-design.md
- Implementation: docs/plans/2026-11-04-goldbook-json-import.md
