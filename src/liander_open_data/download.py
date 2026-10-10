"""Download the Liander SBI profile data.

Liander publishes the aggregated SBI profiles as one zip file (~390 MB,
203 CSV files) on its open data page:
https://www.liander.nl/over-ons/open-data

By default the data is stored in a per-user cache directory, so it is
downloaded only once:

* the ``LIANDER_OPEN_DATA_HOME`` environment variable, if set;
* otherwise ``%LOCALAPPDATA%\\liander-open-data`` on Windows and
  ``$XDG_CACHE_HOME/liander-open-data`` (default ``~/.cache/...``) elsewhere.
"""

from __future__ import annotations

import os
import shutil
import sys
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath

__all__ = [
    "DICTIONARY_URL",
    "PROFILES_URL",
    "default_data_dir",
    "download_dictionary",
    "download_profiles",
]

#: Zip with one ``<SBI code>.csv`` per aggregated electricity profile (2023).
PROFILES_URL = (
    "https://alldxpprdstor.blob.core.windows.net/large-content-media/"
    "Geaggregeerde%20SBI-profielen.zip"
)

#: Workbook with the recommended profile per SBI code (electricity, 2023).
DICTIONARY_URL = (
    "https://www.liander.nl/-/media/files/open-data/verbruiksprofielen-gv-elektriciteit-2023/"
    "overzicht-met-per-sbi-code-een-aanbevolen-profiel.xlsx"
)

_CHUNK = 1 << 20  # 1 MiB
_USER_AGENT = "liander-open-data (https://pypi.org/project/liander-open-data/)"

Progress = Callable[[int, int, str], None]


def default_data_dir() -> Path:
    """Directory where downloaded data is cached (see module docs)."""
    env = os.environ.get("LIANDER_OPEN_DATA_HOME")
    if env:
        return Path(env).expanduser()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "liander-open-data"


def _fetch(url: str, target: Path, progress: Progress | None = None) -> Path:
    """Stream ``url`` to ``target`` via a ``.part`` file (atomic on success)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, open(part, "wb") as fh:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while chunk := response.read(_CHUNK):
                fh.write(chunk)
                done += len(chunk)
                if progress is not None:
                    progress(done, total, target.name)
        if total and done != total:
            raise OSError(f"Incomplete download of {url}: {done} of {total} bytes")
        os.replace(part, target)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    return target


def _has_profiles(directory: Path) -> bool:
    return directory.is_dir() and any(p.stem.isdigit() for p in directory.glob("*.csv"))


def download_profiles(
    data_dir: str | Path | None = None,
    *,
    url: str = PROFILES_URL,
    force: bool = False,
    keep_zip: bool = False,
    progress: Progress | None = None,
) -> Path:
    """Download and extract the SBI profile CSVs.

    Does nothing if the profiles were already downloaded (unless ``force``).

    Args:
        data_dir: Base directory; profiles go to ``<data_dir>/Profiles``.
            Defaults to :func:`default_data_dir`.
        url: Location of the zip file (override for mirrors or testing).
        force: Download again even if profiles are already present.
        keep_zip: Keep the downloaded zip file after extraction.
        progress: Optional callback ``progress(bytes_done, bytes_total, name)``.

    Returns:
        The directory containing the ``<SBI code>.csv`` files, ready to pass
        to :func:`~liander_open_data.build_database`.
    """
    base = Path(data_dir) if data_dir is not None else default_data_dir()
    profiles_dir = base / "Profiles"
    if _has_profiles(profiles_dir) and not force:
        return profiles_dir

    zip_path = _fetch(url, base / "sbi-profielen.zip", progress)
    tmp_dir = base / "Profiles.tmp"
    shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            n = 0
            for info in zf.infolist():
                # Use only the bare file name: never trust paths inside the zip.
                name = PurePosixPath(info.filename.replace("\\", "/")).name
                if info.is_dir() or not name.endswith(".csv") or not name[:-4].isdigit():
                    continue
                with zf.open(info) as src, open(tmp_dir / name, "wb") as dst:
                    shutil.copyfileobj(src, dst, _CHUNK)
                n += 1
        if n == 0:
            raise ValueError(f"No '<code>.csv' files found in {url}")
        shutil.rmtree(profiles_dir, ignore_errors=True)
        os.replace(tmp_dir, profiles_dir)
    except BaseException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    finally:
        if not keep_zip:
            zip_path.unlink(missing_ok=True)
    return profiles_dir


def download_dictionary(
    data_dir: str | Path | None = None,
    *,
    url: str = DICTIONARY_URL,
    force: bool = False,
    progress: Progress | None = None,
) -> Path:
    """Download the original *recommended profile per SBI code* workbook.

    The package already bundles a cleaned copy of this dictionary; download
    the workbook only to check for or use a newer version.

    Returns:
        Path of the downloaded ``.xlsx`` file.
    """
    base = Path(data_dir) if data_dir is not None else default_data_dir()
    target = base / "overzicht-met-per-sbi-code-een-aanbevolen-profiel.xlsx"
    if target.exists() and not force:
        return target
    return _fetch(url, target, progress)
