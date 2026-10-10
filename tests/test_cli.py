from __future__ import annotations

from pathlib import Path

import pandas as pd

from liander_open_data import read_dictionary_csv
from liander_open_data.cli import main


def test_build_and_query(tmp_path: Path, profiles_dir: Path, capsys):
    db = str(tmp_path / "cli.db")
    assert main(["build", str(profiles_dir), "-o", db, "-q"]) == 0
    assert "Database written" in capsys.readouterr().out

    assert main(["info", "--db", db]) == 0
    assert "n_profiles: 3" in capsys.readouterr().out

    assert main(["list", "--db", db]) == 0
    assert "0111" in capsys.readouterr().out

    assert main(["lookup", "8411", "--db", db]) == 0
    assert "Algemeen overheidsbestuur" in capsys.readouterr().out

    assert main(["search", "granen", "--db", db]) == 0
    assert "0111" in capsys.readouterr().out

    out = tmp_path / "011.csv"
    assert main(["export", "011", "-o", str(out), "-c", "mean", "p90", "--db", db]) == 0
    df = pd.read_csv(out, index_col=0)
    assert list(df.columns) == ["mean", "p90"]
    assert len(df) == 96


def test_errors_return_nonzero(tmp_path: Path, capsys):
    assert main(["info", "--db", str(tmp_path / "missing.db")]) == 1
    assert "error:" in capsys.readouterr().err


def test_dictionary_export(tmp_path: Path):
    out = tmp_path / "dict.csv"
    assert main(["dictionary", "-o", str(out)]) == 0
    assert len(read_dictionary_csv(out)) > 1000
