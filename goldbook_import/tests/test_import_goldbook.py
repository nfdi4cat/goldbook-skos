import json
import shutil
from pathlib import Path

from rdflib import RDF, SKOS, Literal, URIRef
from voc4cat import config
from voc4cat.convert_v1 import excel_to_rdf_v1

from import_goldbook import main
from mapping import CONCEPT_RULES

REPO = Path(__file__).parents[2]
FIXTURES = Path(__file__).parent / "fixtures"


def test_import_writes_xlsx_that_voc4cat_converts(tmp_path):
    out = tmp_path / "goldbook.xlsx"
    assert main([str(FIXTURES), "--config", str(REPO / "idranges.toml"), "--output", str(out)]) == 0
    config.load_config(config_file=REPO / "idranges.toml")
    graph = excel_to_rdf_v1(
        out, output_type="graph", vocab_config=config.IDRANGES.vocabs["goldbook"]
    )
    cip = URIRef("https://w3id.org/goldbook/01082")
    assert graph.value(cip, SKOS.prefLabel) == Literal("CIP priority", lang="en")
    assert set(graph.objects(cip, SKOS.altLabel)) == {
        Literal("priority", lang="en"),
        Literal("CIP", lang="en"),
    }
    assert len(set(graph.subjects(RDF.type, SKOS.Concept))) == 4


def test_invalid_record_fails_without_writing_xlsx(tmp_path, capsys):
    src = tmp_path / "json"
    src.mkdir()
    shutil.copy(FIXTURES / "C01082.json", src)
    (src / "page.json").write_text("<html>blocked</html>")
    out = tmp_path / "goldbook.xlsx"
    assert main([str(src), "--config", str(REPO / "idranges.toml"), "--output", str(out)]) == 1
    assert not out.exists()
    assert "page.json" in capsys.readouterr().err


def test_directory_without_json_files_fails_without_writing_xlsx(tmp_path, capsys):
    src = tmp_path / "json"
    src.mkdir()
    out = tmp_path / "goldbook.xlsx"
    assert main([str(src), "--config", str(REPO / "idranges.toml"), "--output", str(out)]) == 2
    assert not out.exists()
    assert "No *.json files" in capsys.readouterr().err


def test_missing_output_directory_is_created(tmp_path):
    out = tmp_path / "new" / "dir" / "goldbook.xlsx"
    assert main([str(FIXTURES), "--config", str(REPO / "idranges.toml"), "--output", str(out)]) == 0
    assert out.exists()


def test_failing_rule_stops_import_naming_record_and_field(tmp_path, capsys, monkeypatch):
    monkeypatch.setitem(CONCEPT_RULES, "definition", lambda r, ix: 1 / 0)
    out = tmp_path / "goldbook.xlsx"
    assert main([str(FIXTURES), "--config", str(REPO / "idranges.toml"), "--output", str(out)]) == 1
    assert not out.exists()
    err = capsys.readouterr().err
    assert "'definition'" in err
    assert "16268" in err  # first record in file name order


def test_index_value_becomes_collection_with_member(tmp_path):
    src = tmp_path / "json"
    src.mkdir()
    term = json.loads((FIXTURES / "C01082.json").read_text(encoding="utf-8"))
    term["term"]["index"] = "quantity"
    (src / "C01082.json").write_text(json.dumps(term), encoding="utf-8")
    out = tmp_path / "goldbook.xlsx"
    assert main([str(src), "--config", str(REPO / "idranges.toml"), "--output", str(out)]) == 0
    config.load_config(config_file=REPO / "idranges.toml")
    graph = excel_to_rdf_v1(
        out, output_type="graph", vocab_config=config.IDRANGES.vocabs["goldbook"]
    )
    quantities = URIRef("https://w3id.org/goldbook/90001")
    assert (quantities, RDF.type, SKOS.Collection) in graph
    assert graph.value(quantities, SKOS.prefLabel) == Literal("quantities", lang="en")
    assert set(graph.objects(quantities, SKOS.member)) == {URIRef("https://w3id.org/goldbook/01082")}
