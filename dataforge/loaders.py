import csv

from dataforge.exceptions import LoaderError


def load_csv(path: str) -> list[dict[str, str]]:
    """Read a CSV file and return its rows as a list of dicts.

    Each dict maps column name (from the header row) to that row's
    value for that column. All values come back as strings — type
    conversion is the validators' job, not the loader's.

    Raises:
        LoaderError: if the file doesn't exist or can't be read as CSV.

    Note:
        If `path` points to a directory instead of a file, this will
        raise a raw IsADirectoryError rather than LoaderError. This is
        a known, accepted limitation for this project's scope.
    """
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError as e:
        raise LoaderError(f"file not found: {path}") from e
    except UnicodeDecodeError as e:
        raise LoaderError(f"could not read {path} as text/CSV") from e


def read_header(path: str) -> list[str]:
    """Return the column names from a CSV file's header row.

    load_csv throws the header away once it has built its row dicts,
    but the CLI needs it to confirm that every rule names a column
    that actually exists. Reading a single line is cheap enough that
    opening the file twice beats changing load_csv's return type and
    the code already built on top of it.

    Returns an empty list for a completely empty file, since there is
    no header row to report.

    Raises:
        LoaderError: if the file doesn't exist or can't be read as CSV.
    """
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            # csv.reader, not DictReader — DictReader would parse every
            # row into a dict just to hand back .fieldnames.
            return next(csv.reader(f), [])
    except FileNotFoundError as e:
        raise LoaderError(f"file not found: {path}") from e
    except UnicodeDecodeError as e:
        raise LoaderError(f"could not read {path} as text/CSV") from e
