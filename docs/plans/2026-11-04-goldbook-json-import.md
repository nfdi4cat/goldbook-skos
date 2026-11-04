# Gold Book JSON Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A repeatable import that turns a directory of Gold Book term JSON files into `inbox-excel-vocabs/goldbook.xlsx` for the unchanged voc4cat pipeline, with the field mapping held in one editable table.

**Architecture:** A self-contained uv project in `goldbook_import/`: a Pydantic model validates every term file, a `TermIndex` gives cross-record lookups, a mapping module holds rule tables (target field → function of record and index) that build voc4cat `ConceptV1` rows, and a CLI writes the xlsx with voc4cat's `export_vocabulary_v1`.

**Tech Stack:** Python ≥ 3.12, uv, pydantic v2, voc4cat 1.2.0 (PyPI, as a library), pytest, just.

**Spec:** `docs/plans/2026-11-04-goldbook-json-import-design.md`

## Global Constraints

- voc4cat-tool is used unchanged, pinned `voc4cat==1.2.0` (the version `ci-pr.yml` installs).
- Concept identifier is the Gold Book `id` (five digits); concept IRI = `https://w3id.org/goldbook/` + `id`, e.g. `https://w3id.org/goldbook/01082`.
- Vocabulary name `goldbook`; the xlsx is `inbox-excel-vocabs/goldbook.xlsx` (file stem = vocabulary name).
- Language code of all labels and definitions: `en`.
- `alternate_labels` in `ConceptV1` are joined with `|` (voc4cat's `aggregate_concepts` splits on `|`).
- The mapping lives in `goldbook_import/mapping.py`; changing what goes into SKOS must not require editing the model, the index or the CLI.
- An import never silently skips a record: invalid files and failing rules are reported by file or id, and no xlsx is written.
- Code reading the download must not run from inside `goldbook-download/`; paths are passed as arguments.
- The repo-level config changes (Task 1) are merged to `main` in their own PR before the first import PR, because CI reads `idranges.toml` from `main`.

## Review Focus

1. A label field holding several comma-separated labels (`<em>synonyms</em>: independent component, thermodynamic component`) must yield one alternate label per term; chemical names with commas but no following space (`1,2-dichloroethane`) must stay whole. Test in Task 3.
2. A record whose `status` is not `current` (`onhold`) must still be imported, carrying the status in the editorial note. Test in Task 3.
3. A rule that raises on one record must stop the import with a message naming the record `id` and the target field. Test in Task 3.
4. A directory with several broken files (HTML page, empty file, unknown field) must report every one of them, not only the first. Test in Task 2.
5. The produced xlsx must survive voc4cat's own conversion, so label and IRI reach RDF as intended. Test in Task 4.

---

### Task 1: Configure the `goldbook` vocabulary

**Files:**
- Modify: `idranges.toml`
- Remove: `vocabularies/vocab_example/` (template demo data, replaced by the Gold Book vocabulary)

**Interfaces:**
- Produces: vocabulary `goldbook` in `idranges.toml`, read by Tasks 4 and 5 through `voc4cat.config.load_config`.
- Tests at: voc4cat's config loader (verification command; config has no code of its own).

- [ ] **Step 1: Replace the `vocab_example` sections by `goldbook`**

Keep the file's explanatory comments, renaming `vocab_example` to `goldbook` in them. Values:

| Key | Value |
|---|---|
| `id_length` | `5` |
| `permanent_iri_part` | `"https://w3id.org/goldbook/"` |
| `vocabulary_iri` | `"https://w3id.org/goldbook/"` |
| `prefix` | `"goldbook"` |
| `title` | `"IUPAC Gold Book (SKOS draft)"` |
| `description` | `"Draft SKOS version of the IUPAC Compendium of Chemical Terminology (Gold Book), generated from the Gold Book JSON for feedback. IRIs and content are provisional."` |
| `created_date` | `"2026-11-04"` |
| `creator` | `"David Linke https://orcid.org/0000-0002-5898-1820"` |
| `publisher` | `"International Union of Pure and Applied Chemistry https://ror.org/03ne2zw20"` |
| `custodian` | `"David Linke https://orcid.org/0000-0002-5898-1820"` |
| `repository` | `"https://github.com/nfdi4cat/goldbook-skos"` |
| `checks.allow_delete` | `false` |
| `prefix_map` | `goldbook = "https://w3id.org/goldbook/"` |
| `id_range` (one entry) | `first_id = 1`, `last_id = 16270`, `gh_name = "dalito"`, `name = "David Linke"`, `orcid = "0000-0002-5898-1820"`, `ror_id = "https://ror.org/029hg0311"` |

Remove the second example `id_range` and the commented `accepted_similarity` example's `vocab_example` name (rename to `goldbook`).

- [ ] **Step 2: Delete `vocabularies/vocab_example/`**

Run: `git rm -r vocabularies/vocab_example`

- [ ] **Step 3: Verify voc4cat loads the config and matches Gold Book IRIs**

Run:
```bash
uv run --no-project --with voc4cat==1.2.0 python -c "
from pathlib import Path
from voc4cat import config
config.load_config(config_file=Path('idranges.toml'))
v = config.IDRANGES.vocabs['goldbook']
assert list(config.IDRANGES.vocabs) == ['goldbook']
assert config.ID_PATTERNS['goldbook'].search('https://w3id.org/goldbook/01082').group('identifier') == '01082'
print('ok', v.id_length, v.permanent_iri_part)"
```
Expected: `ok 5 https://w3id.org/goldbook/`

- [ ] **Step 4: Commit**

```bash
git add idranges.toml vocabularies
git commit -m "Configure the goldbook vocabulary"
```

---

### Task 2: Gold Book record model and loader

**Files:**
- Create: `goldbook_import/pyproject.toml`
- Create: `goldbook_import/goldbook_model.py`
- Create: `goldbook_import/tests/fixtures/` with copies of `goldbook-download/gb1000/goldbook_term_08003.json`, `goldbook-download/goldbook-terms/C01082.json`, `goldbook-download/goldbook-terms/A00034.json`, `goldbook-download/goldbook-terms/16268.json`
- Test: `goldbook_import/tests/test_goldbook_model.py`
- Modify: `.gitignore` (add `goldbook_import/.venv/`) if `.venv` is not already ignored

**Interfaces:**
- Produces (in `goldbook_model.py`):
  - `class Definition(BaseModel)`: `id: int`, `text: str`, `sources: list[str]`, `links: list[Link]` (`Link`: `term: str`, `url: str`), plus the other definition keys found in the data (`notes`, `contexts`, `exams`, `seealso`).
  - `class GoldbookTerm(BaseModel)`: required `id: str` (exactly five digits), `title`, `longtitle`, `doi`, `code`, `status`, `definitions: list[Definition]` (at least one), `altoutputs: dict[str, str]`, `citation`, `license`, `collection`, `disclaimer`, `accessed`; optional `synonym`, `acronym`, `initialism`, `abbrev`, `also_defines` (alias `"also defines"`), `mentioned`, `antonym`, `related`, `index`, `intro`.
  - `class LoadError(NamedTuple)`: `path: Path`, `message: str`.
  - `def load_terms(directory: Path) -> tuple[list[GoldbookTerm], list[LoadError]]` — reads every `*.json` in `directory` (not recursive), sorted by file name.
  - `class TermIndex`: `__init__(self, records: list[GoldbookTerm], iri_base: str)`; `by_id: dict[str, GoldbookTerm]`; `by_code: dict[str, GoldbookTerm]`; `iri(self, record: GoldbookTerm) -> str` returns `iri_base + record.id`.
- Tests at: `load_terms` and `TermIndex`.

`extra="forbid"` on the file wrapper (`{"term": ...}`), on `GoldbookTerm` and on `Definition`, so a changed schema fails. Field types for keys not shown above are the implementer's choice, constrained by Step 6.

- [ ] **Step 1: Create `goldbook_import/pyproject.toml`**

```toml
[project]
name = "goldbook-import"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["voc4cat==1.2.0", "pydantic>=2"]

[dependency-groups]
dev = ["pytest"]

[tool.uv]
package = false

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Write the failing tests**

```python
FIXTURES = Path(__file__).parent / "fixtures"

def test_load_terms_reads_real_records():
    records, errors = load_terms(FIXTURES)
    assert errors == []
    # sorted by file name: 16268.json, A00034.json, C01082.json, goldbook_term_08003.json
    assert [r.id for r in records] == ["16268", "00034", "01082", "08003"]
    cip = next(r for r in records if r.code == "C01082")
    assert cip.title == "CIP priority"
    assert cip.synonym == "<em>synonym</em>: priority"
    assert cip.also_defines == "<em>also defines</em>: CIP rules, sequence rules"
    assert cip.definitions[0].links[0].term == "ligands"

def test_load_terms_reports_every_invalid_file(tmp_path):
    shutil.copy(FIXTURES / "C01082.json", tmp_path)
    (tmp_path / "empty.json").write_bytes(b"")
    (tmp_path / "page.json").write_text("<html>blocked</html>")
    extra = json.loads((FIXTURES / "C01082.json").read_text(encoding="utf-8"))
    extra["term"]["unexpected"] = "x"
    (tmp_path / "extra.json").write_text(json.dumps(extra))
    records, errors = load_terms(tmp_path)
    assert [r.code for r in records] == ["C01082"]
    assert sorted(e.path.name for e in errors) == ["empty.json", "extra.json", "page.json"]

def test_term_index_looks_up_by_id_and_code_and_builds_iri():
    records, _ = load_terms(FIXTURES)
    index = TermIndex(records, "https://w3id.org/goldbook/")
    assert index.by_code["C01082"].id == "01082"
    assert index.by_id["01082"].code == "C01082"
    assert index.iri(index.by_id["01082"]) == "https://w3id.org/goldbook/01082"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run --project goldbook_import pytest goldbook_import -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'goldbook_model'`

- [ ] **Step 4: Implement `goldbook_model.py`**

`load_terms` reads bytes and validates with `model_validate_json`; an empty file, invalid JSON and a validation error each become one `LoadError` with pydantic's message.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --project goldbook_import pytest goldbook_import -v`
Expected: 3 passed, no warnings.

- [ ] **Step 6: Verify the model accepts both complete downloads**

Run:
```bash
uv run --project goldbook_import python -c "
import sys; sys.path.insert(0, 'goldbook_import')
from pathlib import Path
from goldbook_model import load_terms
for d in ('goldbook-download/gb1000', 'goldbook-download/goldbook-terms'):
    records, errors = load_terms(Path(d))
    print(d, len(records), len(errors)); [print(' ', e) for e in errors[:5]]"
```
Expected: `0` errors for both directories. If not, adjust field types (not `extra`) until both pass.

- [ ] **Step 7: Commit**

```bash
git add goldbook_import .gitignore
git commit -m "Add Gold Book record model and loader"
```

---

### Task 3: Mapping table

**Files:**
- Create: `goldbook_import/mapping.py`
- Test: `goldbook_import/tests/test_mapping.py`

**Interfaces:**
- Consumes: `GoldbookTerm`, `TermIndex`, `load_terms` from Task 2; `voc4cat.models_v1.ConceptV1`, `MappingV1`.
- Produces (in `mapping.py`):
  - `Rule = Callable[[GoldbookTerm, TermIndex], object]`
  - `def copy(attribute: str) -> Rule` and `def const(value: object) -> Rule`
  - `def split_labels(raw: str | None) -> list[str]` — removes a leading `<em>…</em>: ` and splits on `", "`.
  - `CONCEPT_RULES: dict[str, Rule]` with the entries below; `MAPPING_RULES: dict[str, Rule] = {}`.
  - `class MappingError(Exception)` with attributes `record_id: str`, `field: str`.
  - `def build_rows(model: type[BaseModel], rules: dict[str, Rule], records: list[GoldbookTerm], index: TermIndex) -> list[BaseModel]`
- Tests at: `build_rows` with `CONCEPT_RULES`, and `build_rows` with ad-hoc rule tables.

`CONCEPT_RULES` (initial mapping from the spec):

| Field | Rule |
|---|---|
| `concept_iri` | `index.iri(record)` |
| `language_code` | `const("en")` |
| `preferred_label` | `copy("title")` |
| `definition` | one definition: its `text`; several: `"1. <text1>\n2. <text2>…"` |
| `alternate_labels` | `split_labels` over `synonym`, `acronym`, `initialism`, `abbrev` in that order, joined with `"|"` |
| `source_vocab_iri` | `"https://doi.org/" + record.doi` |
| `source_vocab_license` | `const("https://creativecommons.org/licenses/by-sa/4.0/")` |
| `source_vocab_rights_holder` | `const("International Union of Pure and Applied Chemistry (IUPAC)")` |
| `editorial_note` | `""` for `status == "current"`, else `"Gold Book status: <status>"` |

- [ ] **Step 1: Write the failing tests**

```python
FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://w3id.org/goldbook/"

@pytest.fixture
def concepts():
    records, _ = load_terms(FIXTURES)
    rows = build_rows(ConceptV1, CONCEPT_RULES, records, TermIndex(records, BASE))
    return {row.concept_iri.removeprefix(BASE): row for row in rows}

def test_concept_row_from_record_with_labels(concepts):
    row = concepts["01082"]
    assert row.concept_iri == "https://w3id.org/goldbook/01082"
    assert row.language_code == "en"
    assert row.preferred_label == "CIP priority"
    assert row.alternate_labels == "priority|CIP"
    assert row.source_vocab_iri == "https://doi.org/10.1351/goldbook.C01082"
    assert row.source_vocab_license == "https://creativecommons.org/licenses/by-sa/4.0/"
    assert row.source_vocab_rights_holder == "International Union of Pure and Applied Chemistry (IUPAC)"
    assert row.editorial_note == ""

def test_several_definitions_are_numbered(concepts):
    texts = [d["text"] for d in json.loads((FIXTURES / "A00034.json").read_text(encoding="utf-8"))["term"]["definitions"]]
    assert concepts["00034"].definition == "\n".join(f"{n}. {t}" for n, t in enumerate(texts, 1))

def test_label_field_with_several_labels_is_split(concepts):
    assert concepts["16268"].alternate_labels == "independent component|thermodynamic component"

def test_split_labels_keeps_commas_inside_names():
    assert split_labels("<em>synonym</em>: 1,2-dichloroethane, ethylene dichloride") == ["1,2-dichloroethane", "ethylene dichloride"]

def test_onhold_record_is_imported_with_status_note(concepts):
    assert concepts["16268"].preferred_label == "component"
    assert concepts["16268"].editorial_note == "Gold Book status: onhold"

def test_rule_receives_record_and_index():
    records, _ = load_terms(FIXTURES)
    index = TermIndex(records, BASE)
    rules = {**CONCEPT_RULES, "editorial_note": lambda r, ix: ix.by_code[r.code].longtitle}
    rows = build_rows(ConceptV1, rules, records, index)
    assert {row.editorial_note for row in rows if row.concept_iri == BASE + "01082"} == {"IUPAC Gold Book - CIP priority"}

def test_failing_rule_names_record_and_field():
    records, _ = load_terms(FIXTURES)
    rules = {**CONCEPT_RULES, "definition": lambda r, ix: 1 / 0}
    with pytest.raises(MappingError) as exc:
        build_rows(ConceptV1, rules, records, TermIndex(records, BASE))
    assert (exc.value.field, exc.value.record_id) == ("definition", records[0].id)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --project goldbook_import pytest goldbook_import/tests/test_mapping.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mapping'`

- [ ] **Step 3: Implement `mapping.py`**

`build_rows` calls every rule for every record, wraps any exception in `MappingError` (chained with `from`), and constructs `model(**values)`; fields without a rule keep the model default.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project goldbook_import pytest goldbook_import -v`
Expected: all passed, no warnings.

- [ ] **Step 5: Commit**

```bash
git add goldbook_import/mapping.py goldbook_import/tests/test_mapping.py
git commit -m "Add the Gold Book to voc4cat mapping table"
```

---

### Task 4: Import command

**Files:**
- Create: `goldbook_import/import_goldbook.py`
- Create: `goldbook_import/README.md`
- Modify: `justfile` (recipes `goldbook-import` and `test-import`)
- Test: `goldbook_import/tests/test_import_goldbook.py`

**Interfaces:**
- Consumes: `load_terms`, `TermIndex` (Task 2); `CONCEPT_RULES`, `MAPPING_RULES`, `build_rows`, `MappingError` (Task 3); from voc4cat 1.2.0: `config.load_config`, `config.IDRANGES`, `config.CURIES_CONVERTER_MAP`, `convert_v1.config_to_concept_scheme_v1`, `convert_v1.build_prefixes_v1`, `convert_v1.export_vocabulary_v1`.
- Produces: `def main(argv: list[str] | None = None) -> int` and CLI `import_goldbook.py JSON_DIR [--config PATH] [--output PATH]`; defaults `--config idranges.toml`, `--output inbox-excel-vocabs/goldbook.xlsx`. The vocabulary name is the output file stem. Exit 0 on success, 1 on invalid records or a `MappingError`, 2 on usage errors.
- Tests at: `main(argv)`.

Before `build_prefixes_v1()`, set `config.curies_converter = config.CURIES_CONVERTER_MAP[vocab_name]` (as voc4cat's `rdf_to_excel_v1` does) so the `goldbook` prefix lands in the Prefixes sheet. The `TermIndex` base is the vocabulary's `permanent_iri_part`. `collections` is `[]`; mapping rows are built only if `MAPPING_RULES` is non-empty.

- [ ] **Step 1: Write the failing tests**

```python
REPO = Path(__file__).parents[2]
FIXTURES = Path(__file__).parent / "fixtures"

def test_import_writes_xlsx_that_voc4cat_converts(tmp_path):
    out = tmp_path / "goldbook.xlsx"
    assert main([str(FIXTURES), "--config", str(REPO / "idranges.toml"), "--output", str(out)]) == 0
    config.load_config(config_file=REPO / "idranges.toml")
    graph = excel_to_rdf_v1(out, output_type="graph", vocab_config=config.IDRANGES.vocabs["goldbook"])
    cip = URIRef("https://w3id.org/goldbook/01082")
    assert graph.value(cip, SKOS.prefLabel) == Literal("CIP priority", lang="en")
    assert set(graph.objects(cip, SKOS.altLabel)) == {Literal("priority", lang="en"), Literal("CIP", lang="en")}
    assert len(set(graph.subjects(RDF.type, SKOS.Concept))) == 4

def test_invalid_record_fails_without_writing_xlsx(tmp_path, capsys):
    src = tmp_path / "json"; src.mkdir()
    shutil.copy(FIXTURES / "C01082.json", src)
    (src / "page.json").write_text("<html>blocked</html>")
    out = tmp_path / "goldbook.xlsx"
    assert main([str(src), "--config", str(REPO / "idranges.toml"), "--output", str(out)]) == 1
    assert not out.exists()
    assert "page.json" in capsys.readouterr().err
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --project goldbook_import pytest goldbook_import/tests/test_import_goldbook.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'import_goldbook'`

- [ ] **Step 3: Implement `import_goldbook.py`**

argparse CLI; errors (each `LoadError`, or the `MappingError` with id and field) go to stderr.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project goldbook_import pytest goldbook_import -v`
Expected: all passed. voc4cat log output from `excel_to_rdf_v1` must not appear as warnings; if `No ID pattern found` or similar is logged, the config is not loaded correctly.

- [ ] **Step 5: Add justfile recipes and README**

```just
# Import Gold Book JSON files from a directory into inbox-excel-vocabs/goldbook.xlsx
[group('goldbook')]
goldbook-import json_dir:
  uv run --project goldbook_import python goldbook_import/import_goldbook.py "{{json_dir}}"

# Run the tests of the Gold Book import
[group('goldbook')]
test-import:
  uv run --project goldbook_import pytest goldbook_import
```

`goldbook_import/README.md`: what the import does, the two recipes, where to change the mapping (`mapping.py`, `CONCEPT_RULES`), and the update procedure from the spec (new download → `just goldbook-import <dir>` → PR with the xlsx). Link the design document instead of repeating it.

- [ ] **Step 6: Commit**

```bash
git add goldbook_import justfile
git commit -m "Add the Gold Book import command"
```

---

### Task 5: Pipeline run on the 1000-term download

**Files:** none changed; this task verifies the spec's goal that the xlsx passes the unchanged pipeline.

- [ ] **Step 1: Import the 1000 terms**

Run: `just goldbook-import goldbook-download/gb1000`
Expected: exit 0, `inbox-excel-vocabs/goldbook.xlsx` exists.

- [ ] **Step 2: Run the local pipeline as CI would**

Run: `just clean`, then `GITHUB_ACTIONS=true GITHUB_ACTOR=dalito just check convert docs` with `time`.
Expected: all steps exit 0; `outbox/goldbook.ttl` contains 1000 `skos:Concept`s; note the runtime for the report.

- [ ] **Step 3: Remove the generated xlsx and outbox**

Run: `rm inbox-excel-vocabs/goldbook.xlsx && just clean`
The import PR is opened by David with a freshly generated xlsx; it is not committed on this branch.
