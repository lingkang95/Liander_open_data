from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from liander_open_data import VALUE_COLUMNS, SBICode, build_database

N_POINTS = 96  # one day of 15-minute values


def _write_profile(path: Path, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.date_range("2023-01-01", periods=N_POINTS, freq="15min")
    df = pd.DataFrame(
        rng.random((N_POINTS, len(VALUE_COLUMNS))), index=index, columns=VALUE_COLUMNS
    )
    df.to_csv(path)  # same layout as the Liander files: unnamed index column
    return df


@pytest.fixture
def profiles_dir(tmp_path: Path) -> Path:
    d = tmp_path / "Profiles"
    d.mkdir()
    for seed, code in enumerate(["01", "011", "0111"]):
        _write_profile(d / f"{code}.csv", seed)
    return d


@pytest.fixture
def records() -> list[SBICode]:
    ko = "KO_AGRARIER"
    return [
        SBICode("01", "Landbouw", n_timeseries=138, best_profile=ko, ko_profile=ko,
                corr_standard_profile=0.24, has_profile=True),
        SBICode("011", "Teelt eenjarige gewassen", n_timeseries=68, best_profile="011",
                ko_profile=ko, corr_best_profile=0.30, has_profile=True),
        SBICode("0111", "Teelt van granen", n_timeseries=16, best_profile="0111",
                ko_profile="KO_OVERIG", corr_best_profile=0.51, has_profile=True),
        SBICode("0113", "Teelt van groenten", warning="Pas op", n_timeseries=4,
                best_profile="011", ko_profile=ko),
        SBICode("02", "Bosbouw"),
    ]  # fmt: skip


@pytest.fixture
def db_path(tmp_path: Path, profiles_dir: Path, records: list[SBICode]) -> Path:
    return build_database(profiles_dir, tmp_path / "test.db", dictionary=records)
