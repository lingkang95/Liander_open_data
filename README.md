# liander-open-data

[![PyPI](https://img.shields.io/pypi/v/liander-open-data.svg)](https://pypi.org/project/liander-open-data/)
[![Python](https://img.shields.io/pypi/pyversions/liander-open-data.svg)](https://pypi.org/project/liander-open-data/)
[![License](https://img.shields.io/pypi/l/liander-open-data.svg)](https://pypi.org/project/liander-open-data/)

A lightweight **SQLite database** and Python API for the
[Liander open data](https://www.liander.nl/over-ons/open-data) **SBI load profiles**:
15-minute electricity profiles per Large scale customers for electricity SBI code (Dutch Standard Industrial
Classification), together with Liander's dictionary of the *recommended
profile per SBI code*.

- One portable `.db` file holding all profiles and the SBI dictionary, which
  any SQLite tool can open.
- A small Python API that returns `pandas` DataFrames.
- A `liander-open-data` command line tool.
- The SBI dictionary (1,427 codes) ships with the package and works without
  any download.

## Installation

```bash
pip install liander-open-data
# optional extras: read the original .xlsx dictionary / export Parquet
pip install "liander-open-data[excel,parquet]"
```

## Quick start

Build the database once. The first time, this downloads the profiles from
Liander (~390 MB zip, cached for later) and takes about 1-2 minutes:

```bash
liander-open-data build
```

If you already have the `<SBI code>.csv` files, pass their folder instead:
`liander-open-data build path/to/Profiles`.

Then query it from Python:

```python
from liander_open_data import ProfileDatabase

with ProfileDatabase("liander_profiles.db") as db:
    db.lookup("8411")                        # dictionary entry for an SBI code
    df = db.get_profile("8411", columns=["mean", "p90"])
    rec = db.recommended_profile("84111")    # Liander's recommended profile
    wide = db.get_profiles(["01", "8411"], column="mean", start="2023-06-01")
```

Or from the command line:

```bash
liander-open-data lookup 8411
liander-open-data search onderwijs --with-profile
liander-open-data export 8411 -o 8411.csv --columns mean p90
```

Or with plain SQL:

```sql
SELECT code, AVG(mean) AS avg_load
FROM profile_timeseries
WHERE timestamp BETWEEN '2023-07-01' AND '2023-08-01'
GROUP BY code ORDER BY avg_load DESC;
```

## Documentation

Full documentation, covering the data model, CLI reference, API reference and
the release guide, is in the [`docs/`](docs/) folder. To browse it as a
website locally, run `uv run mkdocs serve`.

## Development

```bash
uv sync --all-groups
uv run pytest
uv run mkdocs serve      # live documentation preview
```

## Data and license

The code is released under the MIT license. The profiles and SBI dictionary
are published by Liander N.V. as open data; check Liander's terms before
redistributing them.
