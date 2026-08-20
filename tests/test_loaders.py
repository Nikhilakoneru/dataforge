import pytest

from dataforge.exceptions import LoaderError
from dataforge.loaders import load_csv


def test_load_csv_returns_rows_as_dicts(tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("name,age\nAlice,30\nBob,25\n")

    rows = load_csv(str(csv_file))

    assert rows == [
        {"name": "Alice", "age": "30"},
        {"name": "Bob", "age": "25"},
    ]


def test_load_csv_missing_file_raises_loader_error(tmp_path):
    missing_path = tmp_path / "does_not_exist.csv"

    with pytest.raises(LoaderError):
        load_csv(str(missing_path))


def test_load_csv_empty_data_returns_empty_list(tmp_path):
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("name,age\n")  # header only, no data rows

    rows = load_csv(str(csv_file))

    assert rows == []


def test_load_csv_invalid_encoding_raises_loader_error(tmp_path):
    bad_file = tmp_path / "bad_encoding.csv"
    bad_file.write_bytes(b"name,age\n\xff\xfe,30\n")  # invalid UTF-8 bytes

    with pytest.raises(LoaderError):
        load_csv(str(bad_file))