import json
from pathlib import Path

import pytest
from voc4cat.models_v1 import ConceptV1

from goldbook_model import TermIndex, load_terms
from mapping import (
    CONCEPT_RULES,
    LABEL_FIELDS,
    MappingError,
    build_collections,
    build_rows,
    split_labels,
)

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


def test_alternate_labels_exclude_title_and_duplicates():
    records, _ = load_terms(FIXTURES)
    cip = next(r for r in records if r.code == "C01082").model_copy(
        update={
            "synonym": "<em>synonyms</em>: priority, CIP priority",
            "abbrev": "<em>abbrev</em>: CIP",
        }
    )
    rows = build_rows(ConceptV1, CONCEPT_RULES, [cip], TermIndex([cip], BASE))
    assert rows[0].alternate_labels == "priority|CIP"


def _labels(**fields):
    """(preferred_label, alternate_labels) of the CIP fixture record with the given fields."""
    records, _ = load_terms(FIXTURES)
    cip = next(r for r in records if r.code == "C01082").model_copy(
        update={**dict.fromkeys(LABEL_FIELDS), **fields}
    )
    row = build_rows(ConceptV1, CONCEPT_RULES, [cip], TermIndex([cip], BASE))[0]
    return row.preferred_label, row.alternate_labels


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("<sup>13</sup>C-HMQC-NOESY", ("¹³C-HMQC-NOESY", "13C-HMQC-NOESY")),
        ("<em>n</em><sup>th</sup>-order effect", ("nᵗʰ-order effect", "nth-order effect")),
        ("MS<sup><i>n</i></sup>", ("MSⁿ", "MSn")),
        ("<em>t</em><sub>1</sub> noise", ("t₁ noise", "t1 noise")),
        ("pH<sub>0.5</sub> or pH<sub>1/2</sub>", ("pH0.5 or pH1/2", "")),
        ("<i>β</i>, <i>β</i><sub>nuc</sub>", ("β, βnuc", "")),
        ("<i>ab initio</i> methods", ("ab initio methods", "")),
        ('<span class="s">LIDAR</span>', ("LIDAR", "")),
        ("M&#xF8;ssbauer effect", ("Møssbauer effect", "")),
    ],
)
def test_title_markup_becomes_unicode_label_with_ascii_alternate(title, expected):
    assert _labels(title=title) == expected


def test_synonym_markup_becomes_unicode_label_with_ascii_alternate():
    assert _labels(synonym="<em>synonym</em>: CO<sub>2</sub> laser") == (
        "CIP priority",
        "CO₂ laser|CO2 laser",
    )


def test_unknown_markup_in_label_names_record_and_field():
    records, _ = load_terms(FIXTURES)
    cip = next(r for r in records if r.code == "C01082").model_copy(
        update={"title": "CIP <b>priority</b>"}
    )
    with pytest.raises(MappingError) as exc:
        build_rows(ConceptV1, CONCEPT_RULES, [cip], TermIndex([cip], BASE))
    assert (exc.value.field, exc.value.record_id) == ("preferred_label", "01082")


def test_rule_for_unknown_field_is_rejected():
    records, _ = load_terms(FIXTURES)
    rules = {**CONCEPT_RULES, "parent_iri": lambda r, ix: "x"}
    with pytest.raises(ValueError, match="parent_iri"):
        build_rows(ConceptV1, rules, records, TermIndex(records, BASE))


def test_invalid_rule_value_names_record_and_field():
    records, _ = load_terms(FIXTURES)
    rules = {**CONCEPT_RULES, "definition": lambda r, ix: None}
    with pytest.raises(MappingError) as exc:
        build_rows(ConceptV1, rules, records, TermIndex(records, BASE))
    assert (exc.value.field, exc.value.record_id) == ("definition", records[0].id)


def _with_index(records, values):
    """Copies of the fixture records with the given index values, by code."""
    return [r.model_copy(update={"index": values.get(r.code)}) for r in records]


def test_concept_with_index_is_member_of_its_collection():
    records, _ = load_terms(FIXTURES)
    records = _with_index(records, {"C01082": "quantity", "A00034": "prefix"})
    rows = build_rows(ConceptV1, CONCEPT_RULES, records, TermIndex(records, BASE))
    members = {row.concept_iri.removeprefix(BASE): row.member_of_collections for row in rows}
    assert members == {"16268": "", "00034": BASE + "90004", "01082": BASE + "90001", "08003": ""}


def test_unknown_index_value_names_record_and_field():
    records, _ = load_terms(FIXTURES)
    records = _with_index(records, {"C01082": "ratio"})
    with pytest.raises(MappingError) as exc:
        build_rows(ConceptV1, CONCEPT_RULES, records, TermIndex(records, BASE))
    assert (exc.value.field, exc.value.record_id) == ("member_of_collections", "01082")


def test_one_collection_per_index_value_in_use():
    records, _ = load_terms(FIXTURES)
    records = _with_index(records, {"C01082": "quantity", "A00034": "unit", "16268": "unit"})
    collections = build_collections(records, TermIndex(records, BASE))
    assert [
        (c.collection_iri, c.language_code, c.preferred_label, c.definition) for c in collections
    ] == [
        (BASE + "90001", "en", "quantities", "Gold Book terms indexed as quantities."),
        (BASE + "90002", "en", "units", "Gold Book terms indexed as units."),
    ]
