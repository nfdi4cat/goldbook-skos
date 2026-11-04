import shutil
from pathlib import Path

from rdflib import RDF, SKOS, Literal, URIRef
from voc4cat import config
from voc4cat.convert_v1 import excel_to_rdf_v1

from import_goldbook import main

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
