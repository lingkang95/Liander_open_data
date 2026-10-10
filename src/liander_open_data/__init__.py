"""Lightweight SQLite database for Liander's open SBI load profiles.

Quick start::

    from liander_open_data import ProfileDatabase, build_database

    build_database()  # downloads the profiles from Liander on first use
    with ProfileDatabase("liander_profiles.db") as db:
        print(db.lookup("8411"))
        df = db.get_profile("8411", columns=["mean", "p90"])
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("liander-open-data")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    __version__ = "0.0.0"

from .database import (
    SCHEMA_VERSION,
    VALUE_COLUMNS,
    ProfileDatabase,
    ProfileNotFoundError,
    build_database,
)
from .dictionary import (
    SBICode,
    load_dictionary,
    normalize_code,
    read_dictionary_csv,
    read_dictionary_excel,
    write_dictionary_csv,
)
from .download import (
    default_data_dir,
    download_dictionary,
    download_profiles,
)

__all__ = [
    "SCHEMA_VERSION",
    "VALUE_COLUMNS",
    "ProfileDatabase",
    "ProfileNotFoundError",
    "SBICode",
    "__version__",
    "build_database",
    "default_data_dir",
    "download_dictionary",
    "download_profiles",
    "load_dictionary",
    "normalize_code",
    "read_dictionary_csv",
    "read_dictionary_excel",
    "write_dictionary_csv",
]
