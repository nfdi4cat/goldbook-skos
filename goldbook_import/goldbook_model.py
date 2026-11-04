"""Pydantic model of an IUPAC Gold Book term file, its loader and a lookup index.

The models forbid unknown keys, so that a change of the Gold Book JSON schema
stops the import instead of silently dropping data.
"""

from pathlib import Path
from typing import Annotated, NamedTuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class GoldbookModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Link(GoldbookModel):
    """A term mentioned in a definition and the Gold Book URL it links to."""

    term: str | None
    url: str | None


class Definition(GoldbookModel):
    id: int
    text: str
    sources: list[str] = []
    links: list[Link] = []
    notes: dict[str, str] = {}
    exams: dict[str, str] = {}
    # The download has an empty list where a definition has no contexts.
    contexts: dict[str, str] | list[str] = {}
    seealso: list[str] = []


class GoldbookTerm(GoldbookModel):
    id: Annotated[str, Field(pattern=r"^[0-9]{5}$")]
    title: str
    longtitle: str
    doi: str
    code: str
    status: str
    definitions: Annotated[list[Definition], Field(min_length=1)]
    altoutputs: dict[str, str]
    citation: str
    license: str
    collection: str
    disclaimer: str
    accessed: str
    synonym: str | None = None
    acronym: str | None = None
    initialism: str | None = None
    abbrev: str | None = None
    also_defines: Annotated[str | None, Field(alias="also defines")] = None
    mentioned: str | None = None
    antonym: str | None = None
    related: str | None = None
    index: str | None = None
    intro: str | None = None


class GoldbookFile(GoldbookModel):
    term: GoldbookTerm


class LoadError(NamedTuple):
    path: Path
    message: str


def load_terms(directory: Path) -> tuple[list[GoldbookTerm], list[LoadError]]:
    """Validate every *.json file in directory, in file name order.

    Returns the valid records and one LoadError per file that is empty, not
    JSON, does not fit the model, or repeats the id of an earlier file.
    """
    records: list[GoldbookTerm] = []
    errors: list[LoadError] = []
    file_of_id: dict[str, Path] = {}
    for path in sorted(directory.glob("*.json")):
        data = path.read_bytes()
        if not data.strip():
            errors.append(LoadError(path, "empty file"))
            continue
        try:
            record = GoldbookFile.model_validate_json(data).term
        except ValidationError as exc:
            errors.append(LoadError(path, str(exc)))
            continue
        if record.id in file_of_id:
            errors.append(
                LoadError(path, f"id {record.id} also in {file_of_id[record.id].name}")
            )
            continue
        file_of_id[record.id] = path
        records.append(record)
    return records, errors


class TermIndex:
    """Lookups over all records, for mapping rules that need other terms."""

    def __init__(self, records: list[GoldbookTerm], iri_base: str) -> None:
        self.iri_base = iri_base
        self.by_id = {record.id: record for record in records}
        self.by_code = {record.code: record for record in records}

    def iri(self, record: GoldbookTerm) -> str:
        """Concept IRI of a record, built from its id."""
        return self.iri_base + record.id
