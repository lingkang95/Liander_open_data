# Contributing

## Set up

```bash
git clone https://github.com/lingkang95/Liander_open_data.git
cd Liander_open_data
uv sync --all-groups
```

## Everyday commands

```bash
uv run pytest                  # tests + doctests
uv run pytest --cov            # with coverage
uv run ruff check .            # lint
uv run ruff format .           # format
uv run mkdocs serve            # docs at http://127.0.0.1:8000
```

The tests use small synthetic CSVs and need no real Liander data.

## Project layout

```text
src/liander_open_data/
├── __init__.py          # public API
├── database.py          # schema, build_database, ProfileDatabase
├── dictionary.py        # SBI workbook parsing, SBICode
├── cli.py               # liander-open-data command
└── data/
    └── sbi_dictionary.csv   # bundled, cleaned dictionary
tests/                   # pytest suite
docs/                    # this documentation (MkDocs Material)
```

## Updating the bundled dictionary

When Liander publishes a new workbook:

```bash
uv run liander-open-data dictionary path/to/new.xlsx -o src/liander_open_data/data/sbi_dictionary.csv
uv run pytest
```

Review the diff of the CSV, add a changelog entry and release a new version.

## Changing the schema

If you change the layout of the tables in `database.py`, bump
`SCHEMA_VERSION`, update [Data model](data-model.md), and note the change in
the changelog.
