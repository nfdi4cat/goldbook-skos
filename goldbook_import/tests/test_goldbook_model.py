import json
import shutil
from pathlib import Path

from goldbook_model import TermIndex, load_terms

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
