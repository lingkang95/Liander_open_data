# Command line

Installing the package provides the `liander-open-data` command (also
available as `python -m liander_open_data`). Commands that read a database
accept `--db PATH` (default: `liander_profiles.db` in the current
directory).

```text
liander-open-data [--version] [-v] COMMAND ...
```

| Command      | Purpose                                                   |
|--------------|-----------------------------------------------------------|
| `build`      | Build the database from the profile CSVs                  |
| `info`       | Show build metadata                                       |
| `list`       | List all stored profiles                                  |
| `lookup`     | Show the dictionary entry of one SBI code                 |
| `search`     | Search codes by description text or code prefix           |
| `export`     | Export a profile to CSV or Parquet                        |
| `dictionary` | Convert the SBI workbook (or the bundled copy) to CSV     |

## `build`

```bash
liander-open-data build PROFILES_DIR [-o OUTPUT] [-d DICTIONARY] [--overwrite] [-q]
```

- `PROFILES_DIR`: directory containing `<SBI code>.csv` files.
- `-o, --output`: database file to create (default `liander_profiles.db`).
- `-d, --dictionary`: `.xlsx` workbook or `.csv` export. Defaults to the
  bundled dictionary.
- `--overwrite`: replace an existing database.
- `-q, --quiet`: hide the progress bar.

## `lookup`

```bash
$ liander-open-data lookup 8411
                  code: 8411
           description: Algemeen overheidsbestuur
               warning: None
          n_timeseries: 638
          best_profile: 841
      standard_profile: KO_KANTOOR_ONDERWIJS
     corr_best_profile: 0.3404778207107602
 corr_standard_profile: 0.2784444209758644
            ko_profile: KO_KANTOOR_ONDERWIJS
           has_profile: True
   recommended_profile: 841
```

Unknown codes fall back to the nearest parent code.

## `search`

```bash
liander-open-data search onderwijs --with-profile
liander-open-data search 85
```

## `export`

```bash
liander-open-data export CODE -o FILE [-c COL ...] [--start TS] [--end TS] [--recommended]
```

- The file extension of `FILE` sets the format: `.parquet` needs the
  `parquet` extra, anything else is written as CSV.
- `--recommended` exports the profile Liander recommends for `CODE` instead
  of `CODE`'s own profile.

```bash
liander-open-data export 8411 -o 8411_summer.csv -c mean p90 \
    --start 2023-06-01 --end 2023-09-01
```

## `dictionary`

```bash
# convert a (newer) workbook to the clean CSV format
liander-open-data dictionary "Overzicht met per SBI-code een aanbevolen profiel.xlsx" -o sbi.csv
# or dump the bundled copy
liander-open-data dictionary -o sbi.csv
```

## Exit status

`0` on success. `1` on an expected error such as a missing file, an unknown
code, or a bad column; the message is printed to stderr.
