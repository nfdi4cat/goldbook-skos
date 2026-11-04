"""Import IUPAC Gold Book term JSON files into a voc4cat v1 xlsx file.

The xlsx is the input of the repository's voc4cat pipeline. Its file stem is
the vocabulary name in idranges.toml.
"""

import argparse
import sys
from pathlib import Path

from voc4cat import config
from voc4cat.convert_v1 import (
    build_prefixes_v1,
    config_to_concept_scheme_v1,
    export_vocabulary_v1,
)
from voc4cat.models_v1 import ConceptV1, MappingV1

from goldbook_model import TermIndex, load_terms
from mapping import (
    CONCEPT_RULES,
    MAPPING_RULES,
    MappingError,
    build_collections,
    build_rows,
)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_dir", type=Path, help="directory with Gold Book term *.json files")
    parser.add_argument("--config", type=Path, default=Path("idranges.toml"), help="voc4cat idranges.toml")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("inbox-excel-vocabs/goldbook.xlsx"),
        help="xlsx file to write; its stem names the vocabulary",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.json_dir.is_dir():
        print(f"Not a directory: {args.json_dir}", file=sys.stderr)
        return 2
    if not any(args.json_dir.glob("*.json")):
        print(f"No *.json files in {args.json_dir}; no xlsx written.", file=sys.stderr)
        return 2
    vocab_name = args.output.stem
    config.load_config(config_file=args.config)
    if vocab_name not in config.IDRANGES.vocabs:
        print(f"Vocabulary {vocab_name!r} is not configured in {args.config}", file=sys.stderr)
        return 2
    vocab_config = config.IDRANGES.vocabs[vocab_name]

    records, errors = load_terms(args.json_dir)
    if errors:
        for error in errors:
            print(f"{error.path.name}: {error.message}", file=sys.stderr)
        print(f"{len(errors)} invalid file(s); no xlsx written.", file=sys.stderr)
        return 1

    index = TermIndex(records, str(vocab_config.permanent_iri_part))
    try:
        concepts = build_rows(ConceptV1, CONCEPT_RULES, records, index)
        collections = build_collections(records, index)
        mappings = build_rows(MappingV1, MAPPING_RULES, records, index) if MAPPING_RULES else []
    except MappingError as exc:
        print(f"{exc}: {exc.__cause__!r}; no xlsx written.", file=sys.stderr)
        return 1

    # Same converter selection as voc4cat's rdf_to_excel_v1, so the
    # vocabulary's own prefix appears in the Prefixes sheet.
    config.curies_converter = config.CURIES_CONVERTER_MAP[vocab_name]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    export_vocabulary_v1(
        config_to_concept_scheme_v1(vocab_config),
        concepts,
        collections,
        mappings,
        build_prefixes_v1(),
        args.output,
    )
    print(f"Wrote {len(concepts)} concepts to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
