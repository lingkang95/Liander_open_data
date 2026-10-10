from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from liander_open_data import ProfileDatabase, build_database, default_data_dir, download_profiles
from liander_open_data.cli import main


@pytest.fixture
def profiles_zip(tmp_path: Path, profiles_dir: Path) -> str:
    """A zip like Liander's, plus entries that must be ignored."""
    path = tmp_path / "sbi.zip"
    with zipfile.ZipFile(path, "w") as zf:
        for csv in profiles_dir.glob("*.csv"):
            zf.write(csv, f"nested/{csv.name}")
        zf.writestr("../../evil.csv", "x")  # path traversal attempt
        zf.writestr("readme.txt", "ignore me")
        zf.writestr("notes.csv", "ignore me")
    return path.as_uri()


def test_download_profiles(tmp_path: Path, profiles_zip: str):
    out = download_profiles(tmp_path / "cache", url=profiles_zip)
    assert out == tmp_path / "cache" / "Profiles"
    assert sorted(p.name for p in out.iterdir()) == ["01.csv", "011.csv", "0111.csv"]
    assert not (tmp_path / "evil.csv").exists()
    assert not (tmp_path / "cache" / "sbi-profielen.zip").exists()  # zip removed

    # Already present: no new download (the URL is not even touched).
    assert download_profiles(tmp_path / "cache", url="file:///does/not/exist.zip") == out


def test_download_force_and_keep_zip(tmp_path: Path, profiles_zip: str):
    download_profiles(tmp_path, url=profiles_zip)
    download_profiles(tmp_path, url=profiles_zip, force=True, keep_zip=True)
    assert (tmp_path / "sbi-profielen.zip").exists()


def test_download_failure_leaves_no_partial_files(tmp_path: Path):
    with pytest.raises(OSError):
        download_profiles(tmp_path, url=(tmp_path / "missing.zip").as_uri())
    assert sorted(p.name for p in tmp_path.iterdir()) == []


def test_default_data_dir_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LIANDER_OPEN_DATA_HOME", str(tmp_path))
    assert default_data_dir() == tmp_path


def test_build_without_dir_uses_cache(monkeypatch, tmp_path: Path, profiles_zip: str):
    cache = tmp_path / "cache"
    download_profiles(cache, url=profiles_zip)
    monkeypatch.setenv("LIANDER_OPEN_DATA_HOME", str(cache))
    path = build_database(db_path=tmp_path / "auto.db")
    with ProfileDatabase(path) as db:
        assert db.profile_codes() == ["01", "011", "0111"]


def test_cli_build_without_dir(monkeypatch, tmp_path: Path, profiles_zip: str, capsys):
    cache = tmp_path / "cache"
    download_profiles(cache, url=profiles_zip)
    monkeypatch.setenv("LIANDER_OPEN_DATA_HOME", str(cache))
    assert main(["build", "-o", str(tmp_path / "cli.db"), "-q"]) == 0
    assert main(["download", "-q"]) == 0  # already cached: no network
    assert "3 profile CSVs" in capsys.readouterr().out
