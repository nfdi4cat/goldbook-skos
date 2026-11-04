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
5. term.code matches the file name, either <code>.json or goldbook_term_<code>.json.

Each bad file is reported on its own line with the reason, and the script exits with 1 if any file
fails.
