# Feedback on the Gold Book JSON data

Data issues found while importing the Gold Book JSON download into SKOS.

## Label fields whose kind does not match their content

The label fields (`synonym`, `acronym`, `initialism`, `abbrev`) start with their kind, singular or plural (`<em>synonym</em>:` or `<em>synonyms</em>:`).
Several labels in a plural field are separated by ", ".
In these records the kind is singular, but the value contains a separator.
The import splits on ", ", so the first group below ends up as wrongly split labels.

Comma is part of a single name:

| id | title | field | value |
|---|---|---|---|
| 09684 | sandwich immunoassay | synonym | two-site, noncompetitive immunoassay |
| 00003 | α, β | synonym | alpha, beta |
| 01511 | Δ, Λ | synonym | delta, lambda |
| 05434 | σ, π | synonym | sigma, pi |
| 08594 | electro-optic parameter | synonym | equilibrium charge, charge flux (ECCF) |

Two labels under a singular kind:

| id | title | field | value |
|---|---|---|---|
| 09176 | low-energy ion scattering spectrometry | acronym | LEIS, LEISS |
| 09177 | medium-energy ion scattering spectrometry | acronym | MEIS, MEISS |

Separator ";" instead of ", ":

| id | title | field | value |
|---|---|---|---|
| 12354 | charge-mediated fragmentation | synonym | heterolytic fragmentation; inductive cleavage |
