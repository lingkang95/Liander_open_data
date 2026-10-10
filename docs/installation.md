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
1.2 GB as CSV, well above the PyPI size limit. Instead, the package downloads
them from [Liander open data](https://www.liander.nl/over-ons/open-data) the
first time you [build the database](quickstart.md#1-build-the-database).

You can also download them separately:

```bash
liander-open-data download
```

The zip (~390 MB) is extracted to a per-user cache folder and then deleted,
so the download happens only once:

| Platform      | Default location                                 |
|---------------|--------------------------------------------------|
| Windows       | `%LOCALAPPDATA%\liander-open-data\Profiles`      |
| macOS / Linux | `~/.cache/liander-open-data/Profiles`            |

To use another location, set the `LIANDER_OPEN_DATA_HOME` environment
variable or pass `--data-dir`.

If you already have the `<SBI code>.csv` files (e.g. downloaded manually),
pass their folder to `liander-open-data build path/to/Profiles` and nothing
is downloaded.

## Installing from source

```bash
git clone https://github.com/lingkang95/Liander_open_data.git
cd Liander_open_data
uv sync --all-groups      # or: pip install -e ".[all]"
```
