# Quick start

## 1. Build the database

Point the builder at the directory that contains the profile CSVs:

```bash
liander-open-data build data/Profiles -o liander_profiles.db
```

```text
[##############################] 203/203 8899
Database written to liander_profiles.db (717 MB)
```

On a laptop this takes under a minute. The bundled SBI dictionary is used
by default. To use a newer workbook from Liander instead, pass it explicitly
(requires the `excel` extra):

```bash
liander-open-data build data/Profiles -o liander_profiles.db \
    --dictionary "data/dictionary/Overzicht met per SBI-code een aanbevolen profiel.xlsx"
```

The same from Python:

```python
from liander_open_data import build_database

build_database("data/Profiles", "liander_profiles.db", overwrite=True)
```

## 2. Look up an SBI code

```python
from liander_open_data import ProfileDatabase

db = ProfileDatabase("liander_profiles.db")

entry = db.lookup("8411")
entry.description          # 'Algemeen overheidsbestuur'
entry.n_timeseries         # 638
entry.best_profile         # '841'  -> best matching measured profile
entry.ko_profile           # 'KO_KANTOOR_ONDERWIJS' -> standard profile
entry.has_profile          # True   -> a profile exists for 8411 itself
```

Codes that are not in the dictionary (for example a 6-digit company code)
can fall back to their parent:

```python
db.lookup("841199", fallback_to_parent=True).code   # '8411'
```

## 3. Load profiles

```python
# One profile, all statistics, indexed by timestamp
df = db.get_profile("8411")

# Selected statistics and a time window (start inclusive, end exclusive)
summer = db.get_profile("8411", columns=["mean", "p90"],
                        start="2023-06-01", end="2023-09-01")

# One statistic for several profiles: one column per SBI code
wide = db.get_profiles(["01", "47", "8411"], column="mean")

# The profile Liander recommends for a code
rec = db.recommended_profile("0113")
```

!!! note "Standard `KO_*` profiles"
    For some codes the best match is a standard profile such as
    `KO_AGRARIER` instead of a measured SBI profile. Those standard profiles
    are not part of this dataset, so `recommended_profile()` raises
    `ProfileNotFoundError` with an explanatory message. Use
    `entry.recommends_measured_profile` to check beforehand.

## 4. Explore the dictionary

```python
db.dictionary("onderwijs", only_with_profile=True)   # search descriptions
db.dictionary("85")                                   # code prefix
db.list_profiles()                                    # all stored profiles
```

The dictionary also works **without a database**:

```python
from liander_open_data import load_dictionary

codes = {r.code: r for r in load_dictionary()}
codes["8520"].recommended_profile
```

## 5. Use SQL

```python
db.query("""
    SELECT code, MAX(p90) AS peak
    FROM profile_values
    GROUP BY code
    ORDER BY peak DESC
    LIMIT 10
""")
```

See the [data model](data-model.md) for all tables and columns.
