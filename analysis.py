"""Calculation and validation logic for the Student Performance Analysis System.

This file contains NO Streamlit code. It only uses pandas and plain Python,
so every function can be tested on its own (see tests/test_analysis.py).

Default rules (all of them can be changed through function arguments):
    * Marks are expected to be between 0 and 100.
    * A student passes only if EVERY selected subject is at least 40.
    * Grade is decided from the overall percentage:
          90 - 100    -> A+
          80 - 89.99  -> A
          70 - 79.99  -> B
          60 - 69.99  -> C
          50 - 59.99  -> D
          below 50    -> F
    * Missing or invalid marks are NEVER treated as zero.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import pandas as pd

# ---------------------------------------------------------------------------
# Default settings
# ---------------------------------------------------------------------------
MIN_MARK = 0.0
MAX_MARK = 100.0
PASS_MARK = 40.0

# (minimum percentage, grade) - checked from the top down.
GRADE_SCALE = [
    (90.0, "A+"),
    (80.0, "A"),
    (70.0, "B"),
    (60.0, "C"),
    (50.0, "D"),
    (0.0, "F"),
]
GRADE_ORDER = [grade for _, grade in GRADE_SCALE]

PASS_LABEL = "Pass"
FAIL_LABEL = "Fail"

# Names of the columns added by calculate_results().
RESULT_COLUMNS = ["Total_Marks", "Average_Marks", "Percentage", "Grade", "Result"]


class ValidationError(ValueError):
    """Raised when the data cannot be used. The message is meant for the user."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
@dataclass
class ValidationReport:
    """Everything we found while checking the marks columns."""

    errors: list = field(default_factory=list)  # problems that block the calculation
    missing_columns: list = field(default_factory=list)
    non_numeric: dict = field(default_factory=dict)  # column -> list of row positions
    missing_values: dict = field(default_factory=dict)  # column -> list of row positions
    out_of_range: dict = field(default_factory=dict)  # column -> list of row positions
    problem_rows: list = field(default_factory=list)  # sorted row positions with any problem

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _to_numeric_keep_blanks(series: pd.Series) -> pd.Series:
    """Convert a column to numbers. Text that is not a number becomes NaN."""
    if pd.api.types.is_bool_dtype(series):
        # True/False is not a mark. Treat it as non-numeric text.
        return pd.Series([float("nan")] * len(series), index=series.index)
    return pd.to_numeric(series, errors="coerce")


def _is_blank(series: pd.Series) -> pd.Series:
    """True where a cell is empty (NaN, None or only spaces)."""
    as_text = series.astype("string").str.strip()
    empty_text = (as_text == "").fillna(False).astype(bool)
    return series.isna() | empty_text


def validate_marks(
    df: pd.DataFrame,
    subject_columns: list,
    min_mark: float = MIN_MARK,
    max_mark: float = MAX_MARK,
) -> ValidationReport:
    """Check the data and describe every problem. The data is NOT changed.

    Row positions in the report are 0-based positions in ``df``.
    """
    report = ValidationReport()

    if df is None or df.empty:
        report.errors.append(
            "The dataset is empty. Please upload a CSV file that contains at least one student row."
        )
        return report

    if not subject_columns:
        report.errors.append(
            "No subject columns were selected. Please choose at least one column that contains marks."
        )
        return report

    if min_mark >= max_mark:
        report.errors.append("The minimum mark must be smaller than the maximum mark.")
        return report

    missing = [c for c in subject_columns if c not in df.columns]
    if missing:
        report.missing_columns = missing
        report.errors.append(
            "These selected subject columns are not in the dataset: " + ", ".join(map(str, missing)) + "."
        )
        return report

    if len(set(subject_columns)) != len(subject_columns):
        report.errors.append("A subject column was selected more than once.")
        return report

    bad_rows = set()
    for col in subject_columns:
        raw = df[col]
        blank = _is_blank(raw)
        numeric = _to_numeric_keep_blanks(raw)

        # Non-numeric: has some content, but it is not a number (e.g. "abc").
        non_numeric_mask = numeric.isna() & ~blank
        # Missing: the cell is empty.
        missing_mask = blank
        # Out of range: a real number that is below min or above max.
        out_mask = numeric.notna() & ((numeric < min_mark) | (numeric > max_mark))

        if non_numeric_mask.any():
            report.non_numeric[col] = _positions(non_numeric_mask)
            report.errors.append(
                f"Column '{col}' has {int(non_numeric_mask.sum())} non-numeric mark(s), "
                "for example text instead of a number."
            )
        if missing_mask.any():
            report.missing_values[col] = _positions(missing_mask)
            report.errors.append(
                f"Column '{col}' has {int(missing_mask.sum())} missing mark(s). "
                "Missing marks are not treated as zero."
            )
        if out_mask.any():
            report.out_of_range[col] = _positions(out_mask)
            report.errors.append(
                f"Column '{col}' has {int(out_mask.sum())} mark(s) outside the valid range "
                f"{min_mark:g} to {max_mark:g}."
            )

        bad_rows.update(_positions(non_numeric_mask | missing_mask | out_mask))

    report.problem_rows = sorted(bad_rows)
    return report


def _positions(mask: pd.Series) -> list:
    """Return the 0-based positions where a boolean mask is True."""
    return [i for i, flag in enumerate(mask.tolist()) if flag]


def split_valid_and_problem_rows(
    df: pd.DataFrame,
    subject_columns: list,
    min_mark: float = MIN_MARK,
    max_mark: float = MAX_MARK,
):
    """Split the data into (good_rows, problem_rows).

    Nothing is hidden: the caller should show the problem rows to the user
    and say that they were left out of the calculation.
    """
    report = validate_marks(df, subject_columns, min_mark, max_mark)
    if report.missing_columns or (report.errors and not report.problem_rows):
        raise ValidationError(" ".join(report.errors))
    problem_mask = pd.Series(False, index=range(len(df)))
    problem_mask.iloc[report.problem_rows] = True
    problem_mask.index = df.index
    return df[~problem_mask].copy(), df[problem_mask].copy()


# ---------------------------------------------------------------------------
# Grade and result helpers
# ---------------------------------------------------------------------------
def assign_grade(percentage: float) -> str:
    """Return the grade letter for one percentage value."""
    if pd.isna(percentage):
        return ""
    for minimum, grade in GRADE_SCALE:
        if percentage >= minimum:
            return grade
    return "F"


def _result_column_names(df: pd.DataFrame) -> dict:
    """Pick names for the new columns. Never overwrite a column the user already has."""
    names = {}
    for name in RESULT_COLUMNS:
        new_name = name
        while new_name in df.columns:
            new_name = "Calculated_" + new_name
        names[name] = new_name
    return names


def calculate_results(
    df: pd.DataFrame,
    subject_columns: list,
    min_mark: float = MIN_MARK,
    max_mark: float = MAX_MARK,
    pass_mark: float = PASS_MARK,
) -> pd.DataFrame:
    """Return a copy of ``df`` with Total, Average, Percentage, Grade and Result added.

    Raises ValidationError if any selected mark is missing, non-numeric or out of range.
    The input DataFrame is never modified.
    """
    report = validate_marks(df, subject_columns, min_mark, max_mark)
    if not report.is_valid:
        raise ValidationError(" ".join(report.errors))

    result = df.copy()
    marks = pd.DataFrame(
        {col: _to_numeric_keep_blanks(df[col]) for col in subject_columns}, index=df.index
    )
    names = _result_column_names(df)

    total = marks.sum(axis=1)
    average = marks.mean(axis=1)
    percentage = (total / (len(subject_columns) * max_mark) * 100).round(2)

    result[names["Total_Marks"]] = total
    result[names["Average_Marks"]] = average.round(2)
    result[names["Percentage"]] = percentage
    # Grade comes from the rounded percentage that the user sees.
    result[names["Grade"]] = percentage.map(assign_grade)
    passed = (marks >= pass_mark).all(axis=1)
    result[names["Result"]] = passed.map({True: PASS_LABEL, False: FAIL_LABEL})
    return result


def result_column_names(results: pd.DataFrame, original_columns: list) -> dict:
    """Find the names of the calculated columns inside a results table.

    The calculated columns are always the last five columns that
    calculate_results() added, so we read them from the end.
    """
    extra = [c for c in results.columns if c not in original_columns]
    if len(extra) != len(RESULT_COLUMNS):
        raise ValidationError("Could not find the calculated result columns.")
    return dict(zip(RESULT_COLUMNS, extra))


# ---------------------------------------------------------------------------
# Summary and chart data
# ---------------------------------------------------------------------------
def summarize_results(results: pd.DataFrame, cols: dict | None = None) -> dict:
    """Basic class statistics. ``cols`` maps RESULT_COLUMNS to real column names."""
    cols = cols or {name: name for name in RESULT_COLUMNS}
    if results.empty:
        return {
            "total_students": 0,
            "passed": 0,
            "failed": 0,
            "class_average_percentage": None,
            "highest_percentage": None,
            "lowest_percentage": None,
        }
    pct = results[cols["Percentage"]]
    status = results[cols["Result"]]
    return {
        "total_students": int(len(results)),
        "passed": int((status == PASS_LABEL).sum()),
        "failed": int((status == FAIL_LABEL).sum()),
        "class_average_percentage": round(float(pct.mean()), 2),
        "highest_percentage": round(float(pct.max()), 2),
        "lowest_percentage": round(float(pct.min()), 2),
    }


def subject_averages(results: pd.DataFrame, subject_columns: list) -> pd.Series:
    """Average mark of each selected subject."""
    marks = pd.DataFrame({c: pd.to_numeric(results[c]) for c in subject_columns})
    return marks.mean().round(2)


def grade_distribution(results: pd.DataFrame, grade_column: str = "Grade") -> pd.Series:
    """Number of students per grade, always listing every grade (even with 0 students)."""
    counts = results[grade_column].value_counts()
    return counts.reindex(GRADE_ORDER, fill_value=0).astype(int)


def pass_fail_distribution(results: pd.DataFrame, result_column: str = "Result") -> pd.Series:
    """Number of students who passed and failed."""
    counts = results[result_column].value_counts()
    return counts.reindex([PASS_LABEL, FAIL_LABEL], fill_value=0).astype(int)


# ---------------------------------------------------------------------------
# Search and filter
# ---------------------------------------------------------------------------
_ID_COLUMN_NAMES = {"id", "studentid", "sid", "rollno", "roll"}


def _column_key(col) -> str:
    return str(col).strip().lower().replace(" ", "_")


def is_name_column(col) -> bool:
    """True for columns that hold names (searched with 'contains')."""
    return "name" in _column_key(col)


def find_search_columns(df: pd.DataFrame) -> list:
    """Find optional ID and name columns (if the dataset has any).

    A column counts when its name contains 'name' or 'roll', or looks like an ID
    column (id, student_id, Student ID, StudentID, id_number ...).
    """
    found = []
    for col in df.columns:
        key = _column_key(col)
        if (
            "name" in key
            or "roll" in key
            or key in _ID_COLUMN_NAMES
            or key.endswith("_id")
            or key.startswith("id_")
        ):
            found.append(col)
    return found


def _normalize_name(value) -> str:
    """Lower-case a name, trim it and collapse repeated spaces. Missing -> empty text."""
    if pd.isna(value):
        return ""
    return " ".join(str(value).split()).casefold()


def _normalize_id(value) -> str:
    """Make IDs comparable: 14, 14.0 and "14.0" all become "14"; "S010" becomes "s010".

    Numeric IDs often turn into decimals (14.0) when a column has a missing value,
    so this keeps ID search working for both numeric and text IDs.
    """
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip().casefold()
    if re.fullmatch(r"-?\d+\.0+", text):
        text = text.split(".")[0]
    return text


def search_mask(df: pd.DataFrame, search_text: str, search_columns: list) -> pd.Series:
    """True for every row that matches the search text.

    * Name columns: case-insensitive "contains" (``jamie`` finds ``Jamie Jones``).
    * ID columns:   exact match (``14`` finds ID 14 only, not 114 or 140).
    * Spaces at the start/end (and repeated spaces) are ignored.
    * An empty search matches every row.
    """
    everyone = pd.Series(True, index=df.index)
    text = " ".join(str(search_text or "").split()).casefold()
    if not text or not search_columns:
        return everyone

    wanted_id = _normalize_id(text)
    mask = pd.Series(False, index=df.index)
    for col in search_columns:
        if col not in df.columns:
            continue
        if is_name_column(col):
            names = df[col].map(_normalize_name)
            mask |= names.str.contains(text, regex=False)
        else:
            mask |= df[col].map(_normalize_id) == wanted_id
    return mask


def filter_results(
    results: pd.DataFrame,
    search_text: str = "",
    search_columns: list | None = None,
    grades: list | None = None,
    statuses: list | None = None,
    grade_column: str = "Grade",
    result_column: str = "Result",
) -> pd.DataFrame:
    """Filter the results table. Every active condition must be true (logical AND).

    * ``search_text``: see ``search_mask()`` (names: partial, IDs: exact, ignores case/spaces).
      Ignored if there are no search columns.
    * ``grades`` / ``statuses``: keep only these values. ``None`` or an empty list
      means "do not filter on this". Rows with a missing grade/result never match
      an active grade/result filter.

    The input table is never changed; a new table is returned.
    """
    keep = search_mask(results, search_text, search_columns or [])
    if grades:
        keep &= results[grade_column].isin(grades)
    if statuses:
        keep &= results[result_column].isin(statuses)
    return results[keep].copy()


def describe_empty_result(
    results: pd.DataFrame,
    search_text: str = "",
    search_columns: list | None = None,
    grades: list | None = None,
    statuses: list | None = None,
    grade_column: str = "Grade",
    result_column: str = "Result",
) -> str:
    """Explain WHY a search/filter combination matched nobody (empty text if it did match)."""
    if not filter_results(results, search_text, search_columns, grades, statuses, grade_column, result_column).empty:
        return ""
    searching = bool(str(search_text or "").strip()) and bool(search_columns)
    if searching:
        found = int(search_mask(results, search_text, search_columns or []).sum())
        if found == 0:
            return "No students found matching your search."
        if grades or statuses:
            return (
                f"{found} student(s) match your search, but none of them also satisfy "
                "the selected Grade / Pass-Fail filters."
            )
    return "No students satisfy the selected Grade / Pass-Fail filters."


def student_details_table(student: pd.Series) -> pd.DataFrame:
    """One student's row as a two-column table (Field, Value) using only real data.

    Missing cells are shown as "(missing)" - nothing is invented or filled in.
    """

    def show(value) -> str:
        if pd.isna(value):
            return "(missing)"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    return pd.DataFrame({"Field": [str(c) for c in student.index], "Value": [show(v) for v in student.values]})


def count_missing_cells(df: pd.DataFrame, columns: list | None = None) -> int:
    """Number of empty cells in the given columns (all columns by default)."""
    subset = df if columns is None else df[[c for c in columns if c in df.columns]]
    return int(subset.isna().sum().sum())


def result_column_clashes(df: pd.DataFrame) -> list:
    """Columns the uploaded file already has with the same name as a calculated column."""
    return [name for name in RESULT_COLUMNS if name in df.columns]


# ---------------------------------------------------------------------------
# Loading and exporting
# ---------------------------------------------------------------------------
def load_csv(file_like) -> pd.DataFrame:
    """Read a CSV (path or file-like object). Raises ValidationError for unusable files."""
    if hasattr(file_like, "seek"):
        file_like.seek(0)  # Streamlit re-runs the script often; always read from the start.
    try:
        df = pd.read_csv(file_like)
    except pd.errors.EmptyDataError:
        raise ValidationError("The CSV file is empty. Please upload a file that has a header row and data.")
    except pd.errors.ParserError as exc:
        raise ValidationError(f"The file could not be read as a CSV: {exc}")
    except UnicodeDecodeError:
        raise ValidationError(
            "The file could not be read because of its text encoding. "
            "Please save it as a UTF-8 CSV (in Excel: Save As > 'CSV UTF-8') and try again."
        )
    df.columns = [str(c).strip() for c in df.columns]
    if len(df.columns) == 1 and any(sep in df.columns[0] for sep in (";", "\t")):
        raise ValidationError(
            "This file seems to separate columns with semicolons (;) or tabs instead of commas. "
            "Please save it as a comma-separated CSV and try again."
        )
    if df.empty:
        raise ValidationError("The CSV file has column names but no student rows.")
    return df


_NON_MARK_WORDS = ("attendance", "percent", "total", "grade", "result", "submitted", "gender", "status")
_NON_MARK_TOKENS = {"age", "year", "semester", "rank", "gpa", "cgpa", "class", "section"}


def _looks_like_non_mark_column(col) -> bool:
    """True for columns that are numbers but not subject marks (age, attendance, totals ...).

    Only used for the automatic suggestion. The user can still select any column.
    """
    key = _column_key(col)
    tokens = set(re.split(r"[^a-z0-9]+", key))
    return bool(tokens & _NON_MARK_TOKENS) or any(word in key for word in _NON_MARK_WORDS)


def suggest_subject_columns(df: pd.DataFrame) -> list:
    """Guess which columns hold marks (the user can always change this).

    A column is suggested when it is not an ID/name column and at least half of
    its filled-in cells are numbers. "At least half" (instead of "all") is on
    purpose: a marks column with one typo such as "abc" is still suggested, so the
    typo is reported by validate_marks() instead of the column being ignored.
    """
    id_like = set(find_search_columns(df))
    suggested = []
    for col in df.columns:
        if col in id_like or pd.api.types.is_bool_dtype(df[col]) or _looks_like_non_mark_column(col):
            continue
        filled = ~_is_blank(df[col])
        if not filled.any():
            continue
        numeric = _to_numeric_keep_blanks(df[col])
        if numeric[filled].notna().mean() >= 0.5:
            suggested.append(col)
    return suggested


def results_to_csv(results: pd.DataFrame) -> bytes:
    """Convert a results table to CSV bytes (UTF-8, no index column)."""
    buffer = io.StringIO()
    results.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")
