# The data

## Profile CSVs

Each file `<SBI code>.csv` contains one calendar year (2023) of 15-minute
values, 35,040 rows in total. Each row holds statistics over all metered
connections of businesses registered under that SBI code:

| Column          | Meaning                                                        |
|-----------------|----------------------------------------------------------------|
| *(index)*       | Timestamp of the start of the 15-minute interval               |
| `min`           | Minimum over all connections                                   |
| `p10`           | 10th percentile                                                |
| `median`        | Median                                                         |
| `mean`          | Mean                                                           |
| `p90`           | 90th percentile                                                |
| `max`           | Maximum                                                        |
| `median_renorm` | Median, renormalised                                           |
| `mean_renorm`   | Mean, renormalised                                             |
| `p90_renorm`    | 90th percentile, renormalised                                  |

Values are normalised and dimensionless, in the range 0 to 1. Use them as a
*shape* and scale it to an actual consumption (see [Recipes](recipes.md)).

!!! info "Timestamps"
    The source files contain exactly 365 × 96 = 35,040 points with no
    daylight-saving gaps or duplicates. Timestamps are stored as given,
    without a time zone.

SBI codes are hierarchical: `84` → `842` → `8423` → `84232`. Profiles exist
at several levels, and a profile at a higher level aggregates more
connections.

## SBI dictionary

The workbook *Overzicht met per SBI-code een aanbevolen profiel.xlsx* lists
all 1,427 SBI codes. The package renames its columns to English:

| Workbook column                     | Field                   | Description                                                  |
|-------------------------------------|-------------------------|--------------------------------------------------------------|
| `code`                              | `code`                  | SBI code (string, leading zeros kept)                        |
| `description`                       | `description`           | Dutch description                                            |
| `Warning`                           | `warning`               | Set when < 10 time series were available (less reliable)     |
| `Tijdseries in deze SBI`            | `n_timeseries`          | Number of connections behind the profile                     |
| `Profiel hoogste correlatie`        | `best_profile`          | Profile with the highest correlation (SBI code or `KO_*`)    |
| `Standaard profiel`                 | `standard_profile`      | Standard `KO_*` profile for the sector                       |
| `correlatie geaggregeerde profiel`  | `corr_best_profile`     | Correlation with `best_profile`                              |
| `correlatie standaard profiel`      | `corr_standard_profile` | Correlation with `standard_profile`                          |
| `KO_profiel`                        | `ko_profile`            | Recommended standard profile                                 |
| `Profiel aanwezig`                  | `has_profile`           | A measured profile exists for this exact code                |

### Cleaning rules

The parser applies these rules to the raw workbook:

- Codes are kept as strings. Codes that lost their leading zero in Excel
  (`2`, `6`, `8`, `9`) are restored to `02`, `06`, `08`, `09`.
- `"NA"`, `"nan"`, empty cells and the placeholder `0` in text columns become
  `None`.
- A correlation of exactly `0` is a placeholder for *not computed* and
  becomes `None`.
- Leading and trailing whitespace is stripped from descriptions.
- In the database, `has_profile` is recomputed from the CSV files actually
  loaded, so it always matches the `profiles` table.

### Standard profiles (`KO_*`)

Values such as `KO_INDUSTRIE`, `KO_KANTOOR_ONDERWIJS`, `KO_AGRARIER`,
`KO_GLASTUINBOUW`, `KO_LOGISTIEK` and `KO_OVERIG` refer to standard
profiles. They are **not** included in the profile CSVs. `Onbekend` means
*unknown*, and `Onbekend, geen eans` means *unknown, no connections (EANs)*.
