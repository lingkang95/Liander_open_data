from __future__ import annotations

from pathlib import Path

import pytest

from liander_open_data import (
    SBICode,
    load_dictionary,
    normalize_code,
    read_dictionary_csv,
    read_dictionary_excel,
    write_dictionary_csv,
)
from liander_open_data.dictionary import COLUMN_MAP


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0119", "0119"),
        (2, "02"),
        ("2", "02"),
        (8411.0, "8411"),
        (" 841 ", "841"),
        ("01.csv", "01"),
    ],
)
def test_normalize_code(raw, expected):
    assert normalize_code(raw) == expected


@pytest.mark.parametrize("raw", ["KO_OVERIG", "", "12a"])
def test_normalize_code_rejects_invalid(raw):
    with pytest.raises(ValueError):
        normalize_code(raw)


def test_sbicode_properties():
    rec = SBICode("8411", best_profile="841", ko_profile="KO_KANTOOR_ONDERWIJS")
    assert rec.level == 4
    assert rec.parent_code == "841"
    assert rec.recommended_profile == "841"
    assert rec.recommends_measured_profile
    assert SBICode("01").parent_code is None

    ko = SBICode("01", best_profile="KO_AGRARIER")
    assert not ko.recommends_measured_profile
    assert SBICode("02", ko_profile="KO_OVERIG").recommended_profile == "KO_OVERIG"


def test_bundled_dictionary():
    records = load_dictionary()
    codes = [r.code for r in records]
    assert len(records) > 1000
    assert len(codes) == len(set(codes))
    assert all(c.isdigit() and len(c) >= 2 for c in codes)
    by_code = {r.code: r for r in records}
    assert by_code["8411"].best_profile == "841"
    assert by_code["02"].description.startswith("Bosbouw")  # leading zero restored


def test_csv_roundtrip(tmp_path: Path, records):
    path = tmp_path / "dict.csv"
    write_dictionary_csv(records, path)
    assert read_dictionary_csv(path) == records


def test_read_excel_cleans_placeholders(tmp_path: Path):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(list(COLUMN_MAP))
    ws.append(
        ["01", "Landbouw ", None, 138, "KO_AGRARIER", "KO_AGRARIER", "NA", 0.24, "KO_AGRARIER", 1]
    )
    ws.append(["011", "Teelt", None, 68, "011", "KO_AGRARIER", 0.3, 0.2, "KO_AGRARIER", 1])
    ws.append(["2", "Bosbouw", None, None, None, 0, 0, 0, "nan", 0])
    path = tmp_path / "dict.xlsx"
    wb.save(path)

    records = {r.code: r for r in read_dictionary_excel(path)}
    assert set(records) == {"01", "011", "02"}
    assert records["01"].description == "Landbouw"
    assert records["01"].corr_best_profile is None
    assert records["01"].has_profile is True
    assert records["02"] == SBICode("02", "Bosbouw")
    assert load_dictionary(path) == list(records.values())


def test_duplicate_codes_rejected(tmp_path: Path):
    path = tmp_path / "dup.csv"
    write_dictionary_csv([SBICode("01"), SBICode("1")], path)
    with pytest.raises(ValueError, match="Duplicate"):
        read_dictionary_csv(path)
