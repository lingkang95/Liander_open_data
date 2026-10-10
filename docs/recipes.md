# Recipes

## Scale a profile to an annual consumption

Profiles are normalised. To estimate a 15-minute load curve for a business
with a known annual consumption, scale the `mean` profile so that it sums to
that total:

```python
from liander_open_data import ProfileDatabase

annual_kwh = 250_000

with ProfileDatabase("liander_profiles.db") as db:
    shape = db.recommended_profile("8520", columns=["mean"])["mean"]

kwh_per_quarter = shape / shape.sum() * annual_kwh
kw = kwh_per_quarter * 4  # average power in each 15-minute interval
```

## Plot a week

```python
import matplotlib.pyplot as plt

with ProfileDatabase("liander_profiles.db") as db:
    df = db.get_profile("8411", columns=["p10", "median", "p90"],
                        start="2023-03-06", end="2023-03-13")

ax = df["median"].plot(label="median")
ax.fill_between(df.index, df["p10"], df["p90"], alpha=0.3, label="p10-p90")
ax.legend(); plt.show()
```

## Compare sectors

```python
with ProfileDatabase("liander_profiles.db") as db:
    wide = db.get_profiles(["10", "52", "85", "86"], column="mean")

wide.groupby(wide.index.hour).mean().plot(title="Average daily shape")
```

## Map a list of companies to profiles

```python
import pandas as pd
from liander_open_data import ProfileDatabase, ProfileNotFoundError

companies = pd.DataFrame({"name": ["A", "B", "C"], "sbi": ["8411", "01133", "4711"]})

with ProfileDatabase("liander_profiles.db") as db:
    def recommend(code):
        try:
            return db.lookup(code, fallback_to_parent=True).recommended_profile
        except ProfileNotFoundError:
            return None

    companies["profile"] = companies["sbi"].map(recommend)
```

## Use from other tools

=== "sqlite3 CLI"

    ```bash
    sqlite3 liander_profiles.db "SELECT code, description FROM sbi_codes WHERE has_profile"
    ```

=== "DuckDB"

    ```sql
    INSTALL sqlite; LOAD sqlite;
    ATTACH 'liander_profiles.db' AS liander (TYPE sqlite);
    SELECT code, avg(mean) FROM liander.profile_values GROUP BY code;
    ```

=== "R"

    ```r
    con <- DBI::dbConnect(RSQLite::SQLite(), "liander_profiles.db")
    DBI::dbGetQuery(con, "SELECT * FROM profile_timeseries WHERE code = '8411'")
    ```
