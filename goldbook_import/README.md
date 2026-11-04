# Gold Book JSON import

Turns a directory of IUPAC Gold Book term JSON files into `inbox-excel-vocabs/goldbook.xlsx`, the input of this repository's voc4cat pipeline.
Design: [docs/plans/2026-11-04-goldbook-json-import-design.md](../docs/plans/2026-11-04-goldbook-json-import-design.md).

## Usage

Run from the repository root (requires [uv](https://docs.astral.sh/uv/) and [just](https://github.com/casey/just)):

```shell
just goldbook-import goldbook-download/gb1000   # writes inbox-excel-vocabs/goldbook.xlsx
just test-import                                 # runs the tests
```

just runs recipes in the repository root, so the directory given to `goldbook-import` is relative to the repository root, wherever just is called from.

The import validates every file first and writes nothing if any file is invalid or a mapping rule fails; the error names the file or the Gold Book id.

## Changing the mapping

The mapping is the rule table `CONCEPT_RULES` in [mapping.py](mapping.py): each `ConceptV1` field maps to a function that receives one Gold Book record and the `TermIndex` of all records.
Fields without a rule keep the voc4cat default.
`MAPPING_RULES` is the same for `MappingV1` (external mappings) and is empty for now.

## Updating from IUPAC

1. Get a new download of the Gold Book term JSON files.
2. `just goldbook-import <download-dir>`
3. Open a pull request with the generated `inbox-excel-vocabs/goldbook.xlsx`; the CI converts it and commits the vocabulary files.
