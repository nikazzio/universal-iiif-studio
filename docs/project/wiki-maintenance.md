# Wiki Maintenance

The canonical documentation lives in the docs site. The GitHub Wiki is only an orientation layer.

## Source Of Truth

- canonical documentation lives under `docs/`;
- `docs/wiki/` stores the source pages for the published GitHub Wiki;
- the GitHub Wiki itself is not an editable source.

## Publishing Model

- wiki pages stay short;
- canonical links from wiki pages should point to the public docs site;
- repository markdown file URLs should not be the main navigation path for readers.

## Operational Rule

If a topic requires depth, keep that depth in the docs site and link to it from the wiki. Do not rebuild a second full documentation set inside `docs/wiki/`.

## Required Wiki Pages

- `Home.md`
- `Getting-Started.md`
- `Common-Workflows.md`
- `Troubleshooting.md`
- `FAQ.md`
