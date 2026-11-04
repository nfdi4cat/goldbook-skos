# Bringing IUPAC gold book to SKOS

Repository for the goldbook hacking section in [Ontologies4Chem](https://nfdi4chem.de/event/5th-ontologies4chem-workshop/) workshop on Nov 3-5th, 2026 in Limburg.

Sources of goldbooks data:
 * https://goldbook.iupac.org/pages/api/ (API access currently Cloudflare blocked)

Added record checks to scripts/check_json_files.py. Both download folders pass:

- goldbook-download/gb1000: 1000 files checked, 0 invalid.
- goldbook-download/goldbook-terms: 14149 files checked, 0 invalid.

For each .json file the script checks that:
1. it is not empty and parses as JSON;
2. the top level is an object with exactly one key, term;
3. term is an object;
4. term has all 13 fields that every record has today (id, title, longtitle, doi, code, status,
   definitions, altoutputs, citation, license, collection, disclaimer, accessed);
5. term.code matches the file name, either `<code>.json` or `goldbook_term_<code>.json`.

Each bad file is reported on its own line with the reason, and the script exits with 1 if any file
fails.

## Mapping of Gold Book JSON to SKOS

The import ([goldbook_import](goldbook_import/README.md)) maps each Gold Book term file to one `skos:Concept`.
The mapping is provisional; its source of truth is `CONCEPT_RULES` in [goldbook_import/mapping.py](goldbook_import/mapping.py).
All labels and definitions get the language tag `@en`.

| JSON element (`term.…`) | SKOS / RDF property | Comment |
|---|---|---|
| `id` | concept IRI, `dcterms:identifier` | IRI `https://w3id.org/goldbook/<id>` (provisional namespace); voc4cat derives the identifier from the IRI |
| `title` | `skos:prefLabel` | HTML markup kept as is |
| `longtitle` | (not mapped) | "IUPAC Gold Book - " + `title` |
| `doi` | `prov:hadPrimarySource` | as `https://doi.org/<doi>`; the DOI uses `code`, not `id` |
| `code` | (not mapped) | `id` with an optional letter prefix; used in DOIs and Gold Book URLs |
| `status` | `skos:editorialNote` | only for a status other than `current`: "Gold Book status: &lt;status&gt;" (temporary) |
| `synonym` | `skos:altLabel` | `<em>synonym(s)</em>: ` prefix removed, split on ", "; labels equal to the title and duplicates are dropped |
| `acronym` | `skos:altLabel` | as `synonym` |
| `initialism` | `skos:altLabel` | as `synonym` |
| `abbrev` | `skos:altLabel` | as `synonym` |
| `also defines` | (not mapped) | candidate for a later iteration |
| `mentioned` | (not mapped) | candidate for a later iteration |
| `antonym` | (not mapped) | candidate for a later iteration |
| `related` | (not mapped) | candidate for `skos:related` once voc4cat supports it |
| `index` | `skos:member` (of a `skos:Collection`) | one collection per value: `quantity` → "quantities" (`90001`), `unit` → "units" (`90002`), `constant` → "constants" (`90003`), `prefix` → "prefixes" (`90004`); an unknown value stops the import |
| `intro` | (not mapped) | |
| `definitions[].id` | (not mapped) | |
| `definitions[].text` | `skos:definition` | several definitions are numbered and joined into one text ("1. … 2. …"); HTML and LaTeX kept as is |
| `definitions[].links` | (not mapped) | basis for a planned broader-concept heuristic |
| `definitions[].sources` | (not mapped) | |
| `definitions[].notes` | (not mapped) | |
| `definitions[].contexts` | (not mapped) | |
| `definitions[].exams` | (not mapped) | |
| `definitions[].seealso` | (not mapped) | |
| `altoutputs` | (not mapped) | links to HTML, XML and plain-text versions of the term |
| `citation` | (not mapped) | |
| `license` | `dcterms:license` | constant `https://creativecommons.org/licenses/by-sa/4.0/`, as stated in the text |
| `collection` | (not mapped) | |
| `disclaimer` | (not mapped) | |
| `accessed` | (not mapped) | |
| (none) | `dcterms:rightsHolder` | constant "International Union of Pure and Applied Chemistry (IUPAC)" |

voc4cat tool adds further triples to every concept that do not come from the JSON: `skos:inScheme`, `skos:topConceptOf` (no hierarchy yet), `dcterms:provenance` and `rdfs:seeAlso` (links to the concept's file in this repository), and `dcterms:created`/`dcterms:modified` from the git history.
