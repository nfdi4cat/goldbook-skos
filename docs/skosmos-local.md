# Running Skosmos with the Gold Book vocabulary locally

The Gold Book vocabulary is viewed in a customised Skosmos: the branch `goldbook` of [dalito/Skosmos](https://github.com/dalito/Skosmos/tree/goldbook).
It is Skosmos `v3.5-maintenance` plus two changes:

- EasyRdf from [dalito/easyrdf](https://github.com/dalito/easyrdf/tree/unescape-backslash), which fixes the decoding of backslashes in literals ([sweetrdf/easyrdf#87](https://github.com/sweetrdf/easyrdf/issues/87)). Without it the LaTeX in definitions arrives corrupted.
- The plugin `plugins/mathjax`, which renders the LaTeX in definitions with MathJax ([#6](https://github.com/nfdi4cat/goldbook-skos/issues/6)). Its [README](https://github.com/dalito/Skosmos/blob/goldbook/plugins/mathjax/README.md) describes the workaround for MathJax speech generation.

Changes to the fork go into a `gb-…` branch started from `goldbook` and are merged into `goldbook` by pull request.

Requirements: Docker with Docker Compose, and for this repository uv and just (see [Running the import](../README.md#running-the-import)).
Node.js is only needed for the browser tests.

## One-time setup

1. Clone the fork and switch to the branch:

   ```shell
   git clone https://github.com/dalito/Skosmos.git
   cd Skosmos
   git switch goldbook
   ```

2. Add the vocabulary to `dockerfiles/config/config-docker-compose.ttl`, the configuration that Docker Compose mounts into the Skosmos container.
   Keep this change local; it is not committed to the fork.

   ```turtle
   :goldbook a skosmos:Vocabulary, void:Dataset ;
       dc:title "IUPAC Gold Book Test"@en ;
       skosmos:shortName "goldbook";
       dc:subject :cat_general;
       void:uriSpace "https://w3id.org/goldbook/";
       skosmos:language "en", "de";
       skosmos:defaultLanguage "en";
       skosmos:showTopConcepts true;
       skosmos:showStatistics false;
       skosmos:showDeprecated true;
       skosmos:showDeprecatedChanges true;
       skosmos:groupClass skos:Collection ;
       void:sparqlEndpoint <http://fuseki-cache:80/skosmos/sparql> ;
       skosmos:sparqlGraph <https://w3id.org/goldbook> ;
       skosmos:vocabularyPlugins ("mathjax") .
   ```

   `void:uriSpace` must match the concept IRIs; it enables short page URLs such as `/goldbook/en/page/00035`.
   `skosmos:sparqlGraph` is the graph the vocabulary is loaded into below.

3. Optional, when editing the MathJax plugin: create `docker-compose.override.yml` next to `docker-compose.yml`, so that the container uses the plugin files from the working tree instead of the copy built into the image:

   ```yaml
   services:
     skosmos:
       volumes:
         - type: bind
           source: ./plugins
           target: /var/www/html/plugins
   ```

## Start and stop

From the Skosmos clone:

```shell
docker compose up -d --build
docker compose restart fuseki-cache
```

The restart of the cache follows the Skosmos test setup (`tests/init_containers.sh`): the cache can start before Fuseki is ready and then fails to connect.
Skosmos runs at <http://localhost:9090/>, Fuseki at <http://localhost:9030/>.

The build of the Fuseki image downloads the Fuseki server jar from Maven Central.
If that download fails, download `jena-fuseki-server-<version>.jar` for the `JENA_VERSION` in `docker-compose.yml` into `dockerfiles/jena-fuseki2-docker/`, and in its `Dockerfile` replace the `RUN ./download.sh …` line by `COPY ${FUSEKI_JAR} .` (local change, not committed).

`docker compose down` stops and removes the containers.

## Load the vocabulary

Fuseki keeps no data when its container is recreated, so load the vocabulary after every `docker compose up` that recreates Fuseki.

In this repository, build the turtle file `outbox/goldbook.ttl`, either from the published vocabulary in `vocabularies/` or from a fresh import:

```shell
just join                                       # published vocabulary
just goldbook-import goldbook-download/gb1000   # or: fresh import ...
just check convert                              # ... converted to turtle
```

Load it into the graph configured as `skosmos:sparqlGraph`:

```shell
curl -X PUT -H "Content-Type: text/turtle" -T outbox/goldbook.ttl "http://localhost:9030/skosmos/data?graph=https://w3id.org/goldbook"
```

`PUT` replaces the content of the graph; `POST` would add the triples to those already loaded, so old labels would remain.

The vocabulary is then at <http://localhost:9090/goldbook/en/>; a concept page with formulas is <http://localhost:9090/goldbook/en/page/00035>.

## Browser tests

The Cypress spec `tests/cypress/goldbook/mathjax.cy.js` in the Skosmos clone checks the formula rendering against the running instance with the vocabulary loaded:

```shell
npm install    # once
npx cypress run --config 'specPattern=tests/cypress/goldbook/**/*.cy.js'
```

## When EasyRdf releases the fix

Once a sweetrdf/easyrdf release contains the fix for [sweetrdf/easyrdf#87](https://github.com/sweetrdf/easyrdf/issues/87), remove the `repositories` entry from `composer.json` on `goldbook` and require that release instead of `dev-unescape-backslash#… as 1.19.0`.
