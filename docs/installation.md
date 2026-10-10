# Installation

`liander-open-data` requires Python 3.10 or newer.

=== "pip"

    ```bash
    pip install liander-open-data
    ```

=== "uv"

    ```bash
    uv add liander-open-data
    ```

## Optional extras

| Extra     | Installs   | Needed for                                              |
|-----------|------------|---------------------------------------------------------|
| `excel`   | `openpyxl` | Reading the original Liander `.xlsx` dictionary         |
| `parquet` | `pyarrow`  | `liander-open-data export ... -o file.parquet`          |
| `all`     | both       | Everything                                              |

```bash
pip install "liander-open-data[all]"
```

The only required dependencies are `pandas` and `numpy`. SQLite is part of
the Python standard library.

## Getting the profile data

The package does **not** include the profile time series, which take about
1.2 GB as CSV, well above the PyPI size limit. Download the SBI profiles from
[Liander open data](https://www.liander.nl/over-ons/open-data) and put the
`<SBI code>.csv` files in one directory, e.g.:

```text
data/
├── Profiles/
│   ├── 01.csv
│   ├── 011.csv
│   ├── ...
│   └── 8899.csv
└── dictionary/
    └── Overzicht met per SBI-code een aanbevolen profiel.xlsx   # optional
```

Then [build the database](quickstart.md#1-build-the-database).

## Installing from source

```bash
git clone https://github.com/lingkang95/Liander_open_data.git
cd Liander_open_data
uv sync --all-groups      # or: pip install -e ".[all]"
```
