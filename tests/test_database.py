from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from liander_open_data import (
    VALUE_COLUMNS,
    ProfileDatabase,
    ProfileNotFoundError,
    build_database,
)


@pytest.fixture
def db(db_path: Path):
    with ProfileDatabase(db_path) as database:
        yield database


def test_build_creates_all_profiles(db: ProfileDatabase):
    assert db.profile_codes() == ["01", "011", "0111"]
    meta = db.metadata
    assert meta["n_profiles"] == "3"
    assert meta["n_timestamps"] == "96"
    assert meta["schema_version"] == "1"


def test_profile_roundtrip_is_exact(db: ProfileDatabase, profiles_dir: Path):
    expected = pd.read_csv(profiles_dir / "011.csv", index_col=0, parse_dates=True)
    got = db.get_profile("011")
    assert list(got.columns) == list(VALUE_COLUMNS)
    np.testing.assert_array_equal(got.to_numpy(), expected.to_numpy())
    assert (got.index == expected.index).all()
    assert got.columns.name == "011"


def test_get_profile_columns_and_time_window(db: ProfileDatabase):
    df = db.get_profile(
        "011", columns=["mean", "p90"], start="2023-01-01 01:00", end="2023-01-01 02:00"
    )
    assert list(df.columns) == ["mean", "p90"]
    assert len(df) == 4
    assert df.index[0] == pd.Timestamp("2023-01-01 01:00")


def test_get_profile_errors(db: ProfileDatabase):
    with pytest.raises(ProfileNotFoundError):
        db.get_profile("0113")  # in dictionary but no profile
    with pytest.raises(ValueError, match="Unknown column"):
        db.get_profile("01", columns=["bogus"])


def test_get_profiles_wide(db: ProfileDatabase):
    wide = db.get_profiles(["0111", "01"], column="p90")
    assert list(wide.columns) == ["0111", "01"]
    assert wide.shape == (96, 2)
    np.testing.assert_array_equal(wide["01"].to_numpy(), db.get_profile("01")["p90"].to_numpy())
    assert db.get_profiles().shape == (96, 3)
    assert db.get_profiles(start="2023-01-01 23:00").shape == (4, 3)
    with pytest.raises(ProfileNotFoundError):
        db.get_profiles(["0113"])


def test_lookup(db: ProfileDatabase):
    entry = db.lookup("0113")
    assert entry.warning == "Pas op"
    assert entry.has_profile is False
    assert db.lookup(1).code == "01"
    assert db.lookup("011399", fallback_to_parent=True).code == "0113"
    with pytest.raises(ProfileNotFoundError):
        db.lookup("99")


def test_recommended_profile(db: ProfileDatabase):
    # 0113 has no own profile; the dictionary recommends 011.
    pd.testing.assert_frame_equal(
        db.recommended_profile("0113").rename_axis(columns=None),
        db.get_profile("011").rename_axis(columns=None),
    )
    with pytest.raises(ProfileNotFoundError, match="KO_AGRARIER"):
        db.recommended_profile("01")


def test_dictionary_and_list(db: ProfileDatabase):
    assert list(db.dictionary().index) == ["01", "011", "0111", "0113", "02"]
    assert list(db.dictionary(only_with_profile=True).index) == ["01", "011", "0111"]
    assert list(db.dictionary("011").index) == ["011", "0111", "0113"]
    assert list(db.dictionary("granen").index) == ["0111"]
    profiles = db.list_profiles()
    assert profiles.loc["0111", "n_points"] == 96
    assert profiles.loc["0111", "interval_minutes"] == 15


def test_sql_view(db: ProfileDatabase):
    df = db.query("SELECT * FROM profile_timeseries WHERE code = ? LIMIT 2", ["01"])
    assert list(df.columns) == ["code", "timestamp", *VALUE_COLUMNS]
    assert df["timestamp"].iloc[0] == "2023-01-01 00:00:00"


def test_readonly_by_default(db: ProfileDatabase):
    with pytest.raises(sqlite3.OperationalError):
        db.connection.execute("DELETE FROM profiles")


def test_has_profile_reflects_files(tmp_path: Path, profiles_dir: Path, records):
    (profiles_dir / "0111.csv").unlink()
    path = build_database(profiles_dir, tmp_path / "partial.db", dictionary=records)
    with ProfileDatabase(path) as db:
        assert db.lookup("0111").has_profile is False


def test_profile_missing_from_dictionary_gets_stub(tmp_path, profiles_dir, records):
    path = build_database(profiles_dir, tmp_path / "x.db", dictionary=records[:1])
    with ProfileDatabase(path) as db:
        assert db.lookup("0111").description is None
        assert db.has_profile("0111")


def test_build_refuses_overwrite(db_path: Path, profiles_dir: Path):
    with pytest.raises(FileExistsError):
        build_database(profiles_dir, db_path)
    build_database(profiles_dir, db_path, overwrite=True)


def test_build_rejects_bad_csv(tmp_path: Path, profiles_dir: Path):
    pd.DataFrame({"x": [1]}).to_csv(profiles_dir / "99.csv")
    out = tmp_path / "bad.db"
    with pytest.raises(ValueError, match="missing columns"):
        build_database(profiles_dir, out)
    assert not out.exists()
    assert not out.with_name("bad.db.tmp").exists()


def test_build_errors(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        build_database(tmp_path / "nope", tmp_path / "a.db")
    (tmp_path / "empty").mkdir()
    with pytest.raises(FileNotFoundError):
        build_database(tmp_path / "empty", tmp_path / "a.db")
    with pytest.raises(FileNotFoundError):
        ProfileDatabase(tmp_path / "missing.db")


def test_progress_callback(tmp_path: Path, profiles_dir: Path, records):
    calls = []
    build_database(
        profiles_dir, tmp_path / "p.db", dictionary=records, progress=lambda *a: calls.append(a)
    )
    assert calls == [(1, 3, "01"), (2, 3, "011"), (3, 3, "0111")]
