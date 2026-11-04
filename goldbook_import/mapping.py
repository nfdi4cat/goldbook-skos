"""Mapping of Gold Book records to voc4cat v1 model rows.

Each rule table maps a field of a voc4cat model to a rule: a function that
receives one Gold Book record and the index of all records and returns the
field value. Change the mapping by editing the tables and the functions they
use; fields without a rule keep the model's default.
"""

import re
from collections.abc import Callable

from pydantic import BaseModel, ValidationError
from voc4cat.models_v1 import CollectionV1

from goldbook_model import GoldbookTerm, TermIndex

Rule = Callable[[GoldbookTerm, TermIndex], object]

LABEL_FIELDS = ("synonym", "acronym", "initialism", "abbrev")

# One skos:Collection per value of the Gold Book "index" field: value -> (id, label).
# Ids 90000-99999 are reserved for entities this repository creates (idranges.toml).
INDEX_COLLECTIONS = {
    "quantity": ("90001", "quantities"),
    "unit": ("90002", "units"),
    "constant": ("90003", "constants"),
    "prefix": ("90004", "prefixes"),
}
# Label fields start with their kind, e.g. "<em>synonyms</em>: ".
LABEL_PREFIX = re.compile(r"^\s*<em>[^<]*</em>:\s*")


class MappingError(Exception):
    """A rule failed for one record."""

    def __init__(self, record_id: str, field: str) -> None:
        super().__init__(f"mapping of field {field!r} failed for Gold Book id {record_id}")
        self.record_id = record_id
        self.field = field


def copy(attribute: str) -> Rule:
    """Rule returning the record's attribute unchanged."""
    return lambda record, index: getattr(record, attribute)


def const(value: object) -> Rule:
    """Rule returning the same value for every record."""
    return lambda record, index: value


def split_labels(raw: str | None) -> list[str]:
    """Labels of a Gold Book label field, without the "<em>kind</em>: " prefix.

    Labels are separated by ", "; a comma without a following space belongs
    to a chemical name such as "1,2-dichloroethane".
    """
    if not raw:
        return []
    text = LABEL_PREFIX.sub("", raw)
    return [label.strip() for label in text.split(", ") if label.strip()]


def alternate_labels(record: GoldbookTerm, index: TermIndex) -> str:
    # SKOS requires prefLabel and altLabels to be disjoint; dict keeps first-seen order.
    labels = {
        label: None
        for field in LABEL_FIELDS
        for label in split_labels(getattr(record, field))
        if label != record.title
    }
    return "|".join(labels)


def definition(record: GoldbookTerm, index: TermIndex) -> str:
    texts = [d.text for d in record.definitions]
    if len(texts) == 1:
        return texts[0]
    return "\n".join(f"{n}. {text}" for n, text in enumerate(texts, 1))


def index_collection(record: GoldbookTerm, index: TermIndex) -> str:
    """IRI of the collection for the record's index value; KeyError for an unknown value."""
    if record.index is None:
        return ""
    collection_id, _ = INDEX_COLLECTIONS[record.index]
    return index.iri_base + collection_id


def status_note(record: GoldbookTerm, index: TermIndex) -> str:
    return "" if record.status == "current" else f"Gold Book status: {record.status}"


CONCEPT_RULES: dict[str, Rule] = {
    "concept_iri": lambda record, index: index.iri(record),
    "language_code": const("en"),
    "preferred_label": copy("title"),
    "definition": definition,
    "alternate_labels": alternate_labels,
    "source_vocab_iri": lambda record, index: "https://doi.org/" + record.doi,
    "source_vocab_license": const("https://creativecommons.org/licenses/by-sa/4.0/"),
    "source_vocab_rights_holder": const(
        "International Union of Pure and Applied Chemistry (IUPAC)"
    ),
    "editorial_note": status_note,
    "member_of_collections": index_collection,
}

MAPPING_RULES: dict[str, Rule] = {}


def build_collections(records: list[GoldbookTerm], index: TermIndex) -> list[CollectionV1]:
    """One collection per index value that some record uses, in INDEX_COLLECTIONS order."""
    used = {record.index for record in records}
    return [
        CollectionV1(
            collection_iri=index.iri_base + collection_id,
            language_code="en",
            preferred_label=label,
            definition=f"Gold Book terms indexed as {label}.",
        )
        for value, (collection_id, label) in INDEX_COLLECTIONS.items()
        if value in used
    ]


def build_rows(
    model: type[BaseModel],
    rules: dict[str, Rule],
    records: list[GoldbookTerm],
    index: TermIndex,
) -> list[BaseModel]:
    """One model row per record, with each field computed by its rule."""
    # voc4cat models ignore unknown fields, so a misspelt rule key would be lost silently.
    unknown = sorted(set(rules) - set(model.model_fields))
    if unknown:
        raise ValueError(f"rules for fields that {model.__name__} does not have: {unknown}")
    rows = []
    for record in records:
        values = {}
        for field, rule in rules.items():
            try:
                values[field] = rule(record, index)
            except Exception as exc:
                raise MappingError(record.id, field) from exc
        try:
            rows.append(model(**values))
        except ValidationError as exc:
            raise MappingError(record.id, str(exc.errors()[0]["loc"][0])) from exc
    return rows
