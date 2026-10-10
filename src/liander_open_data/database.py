"""SQLite storage for the Liander SBI load profiles.

All 15-minute profiles and the SBI dictionary are stored in a single SQLite
file.  SQLite ships with Python, needs no server and the resulting file can
be opened from any language or tool (DBeaver, ``sqlite3`` CLI, DuckDB, R...).

Schema overview (see the *Data model* page of the documentation):

``sbi_codes``
    The SBI dictionary, one row per code.
``profiles``
    One row per available profile (an SBI code with a measured profile).
``timestamps``
    The shared time axis: ``slot`` (integer) -> ISO timestamp.
``profile_values``
    Long table ``(code, slot, min, p10, median, ...)``.
``profile_timeseries`` (view)
    ``profile_values`` joined with ``timestamps`` for convenient SQL.
``metadata``
    Key/value information about the build.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .dictionary import SBICode, load_dictionary, normalize_code

__all__ = [
    "SCHEMA_VERSION",
    "VALUE_COLUMNS",
    "ProfileDatabase",
    "ProfileNotFoundError",
    "build_database",
]

log = logging.getLogger(__name__)

#: Bumped whenever the table layout changes in an incompatible way.
SCHEMA_VERSION = 1

#: Statistic columns present in every profile CSV, in storage order.
VALUE_COLUMNS: tuple[str, ...] = (
    "min",
    "p10",
    "median",
    "mean",
    "p90",
    "max",
    "median_renorm",
    "mean_renorm",
    "p90_renorm",
)

_TS_FORMAT = "%Y-%m-%d %H:%M:%S"

_SCHEMA = f"""
CREATE TABLE metadata (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE sbi_codes (
    code                  TEXT PRIMARY KEY,
    description           TEXT,
    level                 INTEGER NOT NULL,
    parent_code           TEXT,
    warning               TEXT,
    n_timeseries          INTEGER,
    best_profile          TEXT,
    standard_profile      TEXT,
    corr_best_profile     REAL,
    corr_standard_profile REAL,
    ko_profile            TEXT,
    has_profile           INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE profiles (
    code             TEXT PRIMARY KEY REFERENCES sbi_codes(code),
    n_points         INTEGER NOT NULL,
    start            TEXT NOT NULL,
    "end"            TEXT NOT NULL,
    interval_minutes INTEGER,
    source_file      TEXT
);

CREATE TABLE timestamps (
    slot      INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL UNIQUE
);

CREATE TABLE profile_values (
    code TEXT    NOT NULL REFERENCES profiles(code),
    slot INTEGER NOT NULL REFERENCES timestamps(slot),
    {", ".join(f"{c} REAL" for c in VALUE_COLUMNS)},
    PRIMARY KEY (code, slot)
) WITHOUT ROWID;

CREATE VIEW profile_timeseries AS
SELECT v.code, t.timestamp, {", ".join(f"v.{c}" for c in VALUE_COLUMNS)}
FROM profile_values AS v
JOIN timestamps AS t USING (slot);
"""


class ProfileNotFoundError(KeyError):
    """Raised when an SBI code or profile is not present in the database."""

    def __str__(self) -> str:  # KeyError quotes its message; undo that.
        return str(self.args[0]) if self.args else ""


# --------------------------------------------------------------------------- #
# Building
# --------------------------------------------------------------------------- #


def _read_profile_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0)
    missing = [c for c in VALUE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}")
    extra = [c for c in df.columns if c not in VALUE_COLUMNS]
    if extra:
        log.warning("%s: ignoring unknown columns %s", path.name, extra)
    df.index = pd.to_datetime(df.index, format="mixed")
    if df.index.has_duplicates:
        raise ValueError(f"{path.name}: duplicate timestamps")
    return df.loc[:, list(VALUE_COLUMNS)].sort_index()


def _infer_interval_minutes(index: pd.DatetimeIndex) -> int | None:
    if len(index) < 2:
        return None
    step = pd.Series(index).diff().dropna().mode()
    return int(step.iloc[0].total_seconds() // 60) if len(step) else None


def _sbi_row(rec: SBICode) -> tuple[Any, ...]:
    return (
        rec.code,
        rec.description,
        rec.level,
        rec.parent_code,
        rec.warning,
        rec.n_timeseries,
        rec.best_profile,
        rec.standard_profile,
        rec.corr_best_profile,
        rec.corr_standard_profile,
        rec.ko_profile,
        int(rec.has_profile),
    )


def build_database(
    profiles_dir: str | Path,
    db_path: str | Path = "liander_profiles.db",
    *,
    dictionary: str | Path | Sequence[SBICode] | None = None,
    overwrite: bool = False,
    progress: Callable[[int, int, str], None] | None = None,
) -> Path:
    """Build (or rebuild) the SQLite database from the profile CSV files.

    Every ``<SBI code>.csv`` file in ``profiles_dir`` becomes one profile.
    The database is written to a temporary file first and only moved into
    place when the build succeeds.

    Args:
        profiles_dir: Directory containing the profile CSVs (e.g. ``0111.csv``).
        db_path: Output path of the SQLite database.
        dictionary: SBI dictionary: a path to the Liander ``.xlsx`` workbook,
            a ``.csv`` export, a sequence of :class:`SBICode` records, or
            ``None`` to use the copy bundled with the package.
        overwrite: Replace ``db_path`` if it already exists.
        progress: Optional callback ``progress(done, total, code)`` invoked
            after each profile is loaded.

    Returns:
        The path of the created database.
    """
    profiles_dir = Path(profiles_dir)
    db_path = Path(db_path)
    if not profiles_dir.is_dir():
        raise FileNotFoundError(f"Profiles directory not found: {profiles_dir}")
    if db_path.exists() and not overwrite:
        raise FileExistsError(f"{db_path} exists; pass overwrite=True to replace it")

    if dictionary is None or isinstance(dictionary, (str, Path)):
        records = load_dictionary(dictionary)
    else:
        records = list(dictionary)
    by_code = {rec.code: rec for rec in records}

    files = sorted(
        (p for p in profiles_dir.glob("*.csv") if p.stem.isdigit()),
        key=lambda p: normalize_code(p.stem),
    )
    if not files:
        raise FileNotFoundError(f"No '<code>.csv' files found in {profiles_dir}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = db_path.with_name(db_path.name + ".tmp")
    tmp_path.unlink(missing_ok=True)

    con = sqlite3.connect(tmp_path)
    try:
        con.execute("PRAGMA journal_mode = OFF")
        con.execute("PRAGMA synchronous = OFF")
        con.executescript(_SCHEMA)

        missing_from_dict = [
            normalize_code(p.stem) for p in files if normalize_code(p.stem) not in by_code
        ]
        for code in missing_from_dict:
            log.warning("Profile %s has no entry in the SBI dictionary", code)
            by_code[code] = SBICode(code=code, has_profile=True)
        con.executemany(
            "INSERT INTO sbi_codes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (_sbi_row(rec) for rec in by_code.values()),
        )

        slots: dict[pd.Timestamp, int] = {}
        placeholders = ",".join("?" * (len(VALUE_COLUMNS) + 2))
        for i, path in enumerate(files, start=1):
            code = normalize_code(path.stem)
            df = _read_profile_csv(path)

            new_ts = [ts for ts in df.index if ts not in slots]
            if new_ts:
                start = len(slots)
                for offset, ts in enumerate(new_ts):
                    slots[ts] = start + offset
                con.executemany(
                    "INSERT INTO timestamps VALUES (?, ?)",
                    ((slots[ts], ts.strftime(_TS_FORMAT)) for ts in new_ts),
                )

            con.execute(
                "INSERT INTO profiles VALUES (?,?,?,?,?,?)",
                (
                    code,
                    len(df),
                    df.index[0].strftime(_TS_FORMAT),
                    df.index[-1].strftime(_TS_FORMAT),
                    _infer_interval_minutes(df.index),
                    path.name,
                ),
            )
            slot_col = [slots[ts] for ts in df.index]
            values = df.astype("float64").to_numpy()
            con.executemany(
                f"INSERT INTO profile_values VALUES ({placeholders})",
                (
                    (code, slot, *(None if v != v else float(v) for v in row))
                    for slot, row in zip(slot_col, values, strict=True)
                ),
            )
            if progress is not None:
                progress(i, len(files), code)

        con.execute("UPDATE sbi_codes SET has_profile = 0")
        con.execute(
            "UPDATE sbi_codes SET has_profile = 1 WHERE code IN (SELECT code FROM profiles)"
        )

        from . import __version__

        meta = {
            "schema_version": str(SCHEMA_VERSION),
            "package_version": __version__,
            "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n_profiles": str(len(files)),
            "n_sbi_codes": str(len(by_code)),
            "n_timestamps": str(len(slots)),
            "value_columns": ",".join(VALUE_COLUMNS),
        }
        con.executemany("INSERT INTO metadata VALUES (?, ?)", meta.items())
        con.commit()
    except BaseException:
        con.close()
        tmp_path.unlink(missing_ok=True)
        raise
    con.close()

    os.replace(tmp_path, db_path)
    return db_path


# --------------------------------------------------------------------------- #
# Querying
# --------------------------------------------------------------------------- #


class ProfileDatabase:
    """Read access to a profile database created by :func:`build_database`.

    Example:
        >>> from liander_open_data import ProfileDatabase
        >>> with ProfileDatabase("liander_profiles.db") as db:   # doctest: +SKIP
        ...     df = db.get_profile("8411", columns=["mean", "p90"])

    Args:
        path: Path to the SQLite database file.
        readonly: Open the file read-only (default). Recommended unless you
            want to add your own tables.
    """

    def __init__(self, path: str | Path = "liander_profiles.db", *, readonly: bool = True):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(
                f"Database not found: {self.path}. "
                "Create it with `liander-open-data build <profiles_dir>`."
            )
        if readonly:
            uri = f"{self.path.resolve().as_uri()}?mode=ro"
            self._con = sqlite3.connect(uri, uri=True, check_same_thread=False)
        else:
            self._con = sqlite3.connect(self.path, check_same_thread=False)
        version = self.metadata.get("schema_version")
        if version != str(SCHEMA_VERSION):
            log.warning(
                "Database schema version %s differs from supported version %s; "
                "consider rebuilding.",
                version,
                SCHEMA_VERSION,
            )

    @classmethod
    def build(
        cls,
        profiles_dir: str | Path,
        db_path: str | Path = "liander_profiles.db",
        **kwargs: Any,
    ) -> ProfileDatabase:
        """Build a database with :func:`build_database` and open it."""
        return cls(build_database(profiles_dir, db_path, **kwargs))

    # -- connection management --------------------------------------------- #

    @property
    def connection(self) -> sqlite3.Connection:
        """The underlying :class:`sqlite3.Connection`, for custom queries."""
        return self._con

    def close(self) -> None:
        """Close the database connection."""
        self._con.close()

    def __enter__(self) -> ProfileDatabase:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"ProfileDatabase({str(self.path)!r})"

    # -- generic ------------------------------------------------------------ #

    def query(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> pd.DataFrame:
        """Run an arbitrary SQL query and return the result as a DataFrame.

        Example:
            >>> db.query(  # doctest: +SKIP
            ...     "SELECT code, AVG(mean) AS avg FROM profile_values GROUP BY code"
            ... )
        """
        return pd.read_sql_query(sql, self._con, params=params)

    @property
    def metadata(self) -> dict[str, str]:
        """Build information (schema version, build time, counts...)."""
        return dict(self._con.execute("SELECT key, value FROM metadata").fetchall())

    # -- dictionary --------------------------------------------------------- #

    def lookup(self, code: str | int, *, fallback_to_parent: bool = False) -> SBICode:
        """Return the dictionary entry for an SBI code.

        Args:
            code: SBI code, e.g. ``"8411"`` or ``8411``.
            fallback_to_parent: If the exact code is unknown, walk up the SBI
                hierarchy (``"84111"`` -> ``"8411"`` -> ``"841"`` ...) and
                return the first match.

        Raises:
            ProfileNotFoundError: If no matching code exists.
        """
        norm = normalize_code(code)
        candidates = [norm]
        if fallback_to_parent:
            candidates += [norm[:n] for n in range(len(norm) - 1, 1, -1)]
        for cand in candidates:
            row = self._con.execute(
                """SELECT code, description, warning, n_timeseries, best_profile,
                          standard_profile, corr_best_profile, corr_standard_profile,
                          ko_profile, has_profile
                   FROM sbi_codes WHERE code = ?""",
                (cand,),
            ).fetchone()
            if row is not None:
                return SBICode(*row[:-1], has_profile=bool(row[-1]))
        raise ProfileNotFoundError(f"SBI code {norm!r} not found in dictionary")

    def dictionary(
        self, search: str | None = None, *, only_with_profile: bool = False
    ) -> pd.DataFrame:
        """Return the SBI dictionary as a DataFrame.

        Args:
            search: Case-insensitive substring to match in the description,
                or a code prefix (e.g. ``"84"``).
            only_with_profile: Only include codes that have a measured profile.
        """
        sql = "SELECT * FROM sbi_codes WHERE 1=1"
        params: list[Any] = []
        if only_with_profile:
            sql += " AND has_profile = 1"
        if search:
            if search.strip().isdigit():
                sql += " AND code LIKE ?"
                params.append(search.strip() + "%")
            else:
                sql += " AND description LIKE ?"
                params.append(f"%{search}%")
        sql += " ORDER BY code"
        return self.query(sql, params).set_index("code")

    # -- profiles ----------------------------------------------------------- #

    def profile_codes(self) -> list[str]:
        """Codes of all profiles stored in the database."""
        return [r[0] for r in self._con.execute("SELECT code FROM profiles ORDER BY code")]

    def has_profile(self, code: str | int) -> bool:
        """Whether a measured profile exists for ``code``."""
        row = self._con.execute(
            "SELECT 1 FROM profiles WHERE code = ?", (normalize_code(code),)
        ).fetchone()
        return row is not None

    def list_profiles(self) -> pd.DataFrame:
        """Overview of all stored profiles, joined with their descriptions."""
        return self.query(
            """SELECT p.code, s.description, s.n_timeseries, s.warning,
                      p.n_points, p.start, p."end", p.interval_minutes
               FROM profiles AS p LEFT JOIN sbi_codes AS s USING (code)
               ORDER BY p.code"""
        ).set_index("code")

    def _check_columns(self, columns: Iterable[str] | None) -> list[str]:
        cols = list(VALUE_COLUMNS) if columns is None else list(columns)
        bad = [c for c in cols if c not in VALUE_COLUMNS]
        if bad:
            raise ValueError(f"Unknown column(s) {bad}; choose from {list(VALUE_COLUMNS)}")
        return cols

    @staticmethod
    def _time_filter(start: Any, end: Any) -> tuple[str, list[str]]:
        sql, params = "", []
        if start is not None:
            sql += " AND t.timestamp >= ?"
            params.append(pd.Timestamp(start).strftime(_TS_FORMAT))
        if end is not None:
            sql += " AND t.timestamp < ?"
            params.append(pd.Timestamp(end).strftime(_TS_FORMAT))
        return sql, params

    def get_profile(
        self,
        code: str | int,
        columns: Iterable[str] | None = None,
        *,
        start: Any = None,
        end: Any = None,
    ) -> pd.DataFrame:
        """Load one profile as a DataFrame indexed by timestamp.

        Args:
            code: SBI code of the profile.
            columns: Subset of :data:`VALUE_COLUMNS` (default: all).
            start: Inclusive lower time bound (anything ``pd.Timestamp`` accepts).
            end: Exclusive upper time bound.

        Raises:
            ProfileNotFoundError: If no profile exists for ``code``.
        """
        norm = normalize_code(code)
        if not self.has_profile(norm):
            raise ProfileNotFoundError(f"No profile stored for SBI code {norm!r}")
        cols = self._check_columns(columns)
        time_sql, time_params = self._time_filter(start, end)
        df = self.query(
            f"""SELECT t.timestamp, {", ".join(f"v.{c}" for c in cols)}
                FROM profile_values AS v JOIN timestamps AS t USING (slot)
                WHERE v.code = ?{time_sql}
                ORDER BY v.slot""",
            [norm, *time_params],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], format=_TS_FORMAT)
        df = df.set_index("timestamp")
        df.columns.name = norm
        return df

    def get_profiles(
        self,
        codes: Iterable[str | int] | None = None,
        column: str = "mean",
        *,
        start: Any = None,
        end: Any = None,
    ) -> pd.DataFrame:
        """Load one statistic for several profiles as a wide DataFrame.

        Args:
            codes: SBI codes to include (default: all profiles).
            column: Which statistic to return, e.g. ``"mean"`` or ``"p90"``.
            start: Inclusive lower time bound.
            end: Exclusive upper time bound.

        Returns:
            DataFrame indexed by timestamp with one column per SBI code.
        """
        (column,) = self._check_columns([column])
        wanted = self.profile_codes() if codes is None else [normalize_code(c) for c in codes]
        missing = [c for c in wanted if not self.has_profile(c)]
        if missing:
            raise ProfileNotFoundError(f"No profile stored for SBI code(s) {missing}")
        time_sql, time_params = self._time_filter(start, end)
        axis = self._con.execute(
            f"SELECT slot, timestamp FROM timestamps AS t WHERE 1=1{time_sql} ORDER BY slot",
            time_params,
        ).fetchall()
        slots = np.array([slot for slot, _ in axis], dtype=np.int64)
        lo, hi = (int(slots.min()), int(slots.max())) if len(slots) else (0, -1)
        position = np.full(hi - lo + 1, -1, dtype=np.int64)
        position[slots - lo] = np.arange(len(slots))

        # Reading per code via the primary key is much faster than one big
        # join + pivot on timestamp strings.
        data = np.full((len(axis), len(wanted)), np.nan)
        for j, code in enumerate(wanted):
            rows = self._con.execute(
                f"SELECT slot, {column} FROM profile_values "
                "WHERE code = ? AND slot BETWEEN ? AND ?",
                (code, lo, hi),
            ).fetchall()
            if not rows:
                continue
            arr = np.array(rows, dtype=np.float64)  # None -> NaN
            pos = position[arr[:, 0].astype(np.int64) - lo]
            keep = pos >= 0
            data[pos[keep], j] = arr[keep, 1]

        index = pd.DatetimeIndex(
            pd.to_datetime([ts for _, ts in axis], format=_TS_FORMAT), name="timestamp"
        )
        wide = pd.DataFrame(data, index=index, columns=pd.Index(wanted, name=column))
        return wide.sort_index()

    def recommended_profile(
        self, code: str | int, columns: Iterable[str] | None = None, **kwargs: Any
    ) -> pd.DataFrame:
        """Load the profile Liander recommends for an SBI code.

        The recommendation (``best_profile`` in the dictionary) may point to
        another SBI code, typically a parent with more data.  Unknown codes
        fall back to their nearest parent in the SBI hierarchy.

        Raises:
            ProfileNotFoundError: If the recommendation is a standard ``KO_*``
                profile, which is not part of this dataset.
        """
        entry = self.lookup(code, fallback_to_parent=True)
        rec = entry.recommended_profile
        if not entry.recommends_measured_profile:
            raise ProfileNotFoundError(
                f"SBI code {entry.code!r} has no measured profile recommendation "
                f"(recommended: {rec!r}); standard KO_* profiles are not part of "
                "this dataset."
            )
        assert rec is not None
        return self.get_profile(rec, columns, **kwargs)
