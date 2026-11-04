import json
from pathlib import Path

import pytest
from voc4cat.models_v1 import ConceptV1

from goldbook_model import TermIndex, load_terms
from mapping import CONCEPT_RULES, MappingError, build_rows, split_labels

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
    assert (
        row.source_vocab_rights_holder
        == "International Union of Pure and Applied Chemistry (IUPAC)"
    )
    assert row.editorial_note == ""


def test_several_definitions_are_numbered(concepts):
    term = json.loads((FIXTURES / "A00034.json").read_text(encoding="utf-8"))["term"]
    texts = [d["text"] for d in term["definitions"]]
    assert len(texts) > 1
    assert concepts["00034"].definition == "\n".join(
        f"{n}. {t}" for n, t in enumerate(texts, 1)
    )


def test_label_field_with_several_labels_is_split(concepts):
    assert (
        concepts["16268"].alternate_labels
        == "independent component|thermodynamic component"
    )


def test_split_labels_keeps_commas_inside_names():
    assert split_labels("<em>synonym</em>: 1,2-dichloroethane, ethylene dichloride") == [
        "1,2-dichloroethane",
        "ethylene dichloride",
    ]


def test_onhold_record_is_imported_with_status_note(concepts):
    assert concepts["16268"].preferred_label == "component"
    assert concepts["16268"].editorial_note == "Gold Book status: onhold"


def test_rule_receives_record_and_index():
    records, _ = load_terms(FIXTURES)
    index = TermIndex(records, BASE)
    rules = {
        **CONCEPT_RULES,
        "editorial_note": lambda r, ix: ix.by_code[r.code].longtitle,
    }
    rows = build_rows(ConceptV1, rules, records, index)
    assert {row.editorial_note for row in rows if row.concept_iri == BASE + "01082"} == {
        "IUPAC Gold Book - CIP priority"
    }


def test_failing_rule_names_record_and_field():
    records, _ = load_terms(FIXTURES)
    rules = {**CONCEPT_RULES, "definition": lambda r, ix: 1 / 0}
    with pytest.raises(MappingError) as exc:
        build_rows(ConceptV1, rules, records, TermIndex(records, BASE))
    assert (exc.value.field, exc.value.record_id) == ("definition", records[0].id)
