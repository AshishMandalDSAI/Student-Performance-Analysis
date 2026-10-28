"""Automated tests for analysis.py.

Run from the project folder with:  python -m pytest -q

Expected values below were worked out by hand, for example
    Asha: 90 + 95 + 100 = 285 total, 285 / 3 = 95 average, 285 / 300 * 100 = 95 percent.
"""

import io
import sys
from pathlib import Path

import pandas as pd
import pytest

# Make "import analysis" work even if pytest is started from another folder.
PROJECT_FOLDER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_FOLDER))

import analysis  # noqa: E402

SUBJECTS = ["Math", "English", "Science"]


@pytest.fixture
def students():
    """Six students that cover every kind of result we want to check."""
    return pd.DataFrame(
        {
            "Student_ID": ["S1", "S2", "S3", "S4", "S5", "S6"],
            "Name": ["Asha", "Ben", "Chitra", "Dev", "Esha", "Farhan"],
            "Math": [90, 80, 70, 30, 45, 55],
            "English": [95, 85, 60, 90, 45, 52],
            "Science": [100, 75, 65, 95, 45, 58],
        }
    )


@pytest.fixture
def results(students):
    return analysis.calculate_results(students, SUBJECTS)


def row(results, name):
    """Get one student's row by name."""
    return results[results["Name"] == name].iloc[0]


# ---------------------------------------------------------------------------
# 1. Valid dataset processing
# ---------------------------------------------------------------------------
def test_valid_dataset_is_processed(students):
    report = analysis.validate_marks(students, SUBJECTS)
    assert report.is_valid
    assert report.errors == []

    results = analysis.calculate_results(students, SUBJECTS)
    assert len(results) == len(students)
    # Original columns are kept, in the same order, and the 5 result columns are added.
    assert list(results.columns) == list(students.columns) + analysis.RESULT_COLUMNS


def test_input_dataframe_is_not_modified(students):
    before = students.copy()
    analysis.calculate_results(students, SUBJECTS)
    pd.testing.assert_frame_equal(students, before)


# ---------------------------------------------------------------------------
# 2-4. Total, average, percentage
# ---------------------------------------------------------------------------
def test_total_marks(results):
    assert row(results, "Asha")["Total_Marks"] == 285
    assert row(results, "Ben")["Total_Marks"] == 240
    assert row(results, "Dev")["Total_Marks"] == 215


def test_average_marks(results):
    assert row(results, "Asha")["Average_Marks"] == pytest.approx(95.0)
    assert row(results, "Dev")["Average_Marks"] == pytest.approx(71.67)  # 215 / 3 = 71.666...
    assert row(results, "Esha")["Average_Marks"] == pytest.approx(45.0)


def test_percentage(results):
    assert row(results, "Asha")["Percentage"] == pytest.approx(95.0)
    assert row(results, "Chitra")["Percentage"] == pytest.approx(65.0)
    assert row(results, "Dev")["Percentage"] == pytest.approx(71.67)


def test_percentage_uses_max_mark_setting():
    df = pd.DataFrame({"Name": ["A"], "Math": [40], "Sci": [30]})
    out = analysis.calculate_results(df, ["Math", "Sci"], max_mark=50, pass_mark=20)
    assert out["Percentage"].iloc[0] == pytest.approx(70.0)  # 70 / (2 * 50) * 100


# ---------------------------------------------------------------------------
# 5. Grade assignment
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "percentage, expected",
    [
        (100, "A+"),
        (90, "A+"),
        (89.99, "A"),
        (80, "A"),
        (79.99, "B"),
        (70, "B"),
        (69.99, "C"),
        (60, "C"),
        (59.99, "D"),
        (50, "D"),
        (49.99, "F"),
        (0, "F"),
    ],
)
def test_assign_grade_boundaries(percentage, expected):
    assert analysis.assign_grade(percentage) == expected


def test_grades_in_results(results):
    assert row(results, "Asha")["Grade"] == "A+"
    assert row(results, "Ben")["Grade"] == "A"
    assert row(results, "Chitra")["Grade"] == "C"
    assert row(results, "Dev")["Grade"] == "B"
    assert row(results, "Esha")["Grade"] == "F"
    assert row(results, "Farhan")["Grade"] == "D"


# ---------------------------------------------------------------------------
# 6. Pass / Fail assignment
# ---------------------------------------------------------------------------
def test_pass_and_fail(results):
    assert row(results, "Asha")["Result"] == "Pass"
    assert row(results, "Esha")["Result"] == "Pass"  # 45 in every subject is above 40
    # Dev has a good average (grade B) but scored 30 in Math, so must Fail.
    assert row(results, "Dev")["Grade"] == "B"
    assert row(results, "Dev")["Result"] == "Fail"


def test_exactly_pass_mark_is_a_pass():
    df = pd.DataFrame({"Math": [40, 40], "English": [40, 39.99]})
    out = analysis.calculate_results(df, ["Math", "English"])
    assert out["Result"].tolist() == ["Pass", "Fail"]


def test_custom_pass_mark():
    df = pd.DataFrame({"Math": [45], "English": [45]})
    assert analysis.calculate_results(df, ["Math", "English"], pass_mark=40)["Result"].iloc[0] == "Pass"
    assert analysis.calculate_results(df, ["Math", "English"], pass_mark=50)["Result"].iloc[0] == "Fail"


# ---------------------------------------------------------------------------
# 7. Missing subject columns
# ---------------------------------------------------------------------------
def test_missing_subject_column(students):
    report = analysis.validate_marks(students, ["Math", "Physics"])
    assert not report.is_valid
    assert report.missing_columns == ["Physics"]
    assert "Physics" in report.errors[0]
    with pytest.raises(analysis.ValidationError, match="Physics"):
        analysis.calculate_results(students, ["Math", "Physics"])


def test_no_subject_columns_selected(students):
    report = analysis.validate_marks(students, [])
    assert not report.is_valid
    assert "No subject columns" in report.errors[0]


# ---------------------------------------------------------------------------
# 8. Non-numeric marks
# ---------------------------------------------------------------------------
def test_non_numeric_marks(students):
    students["Math"] = students["Math"].astype(object)
    students.loc[2, "Math"] = "abc"
    report = analysis.validate_marks(students, SUBJECTS)
    assert not report.is_valid
    assert report.non_numeric == {"Math": [2]}
    assert report.problem_rows == [2]
    with pytest.raises(analysis.ValidationError, match="non-numeric"):
        analysis.calculate_results(students, SUBJECTS)


def test_numbers_stored_as_text_are_accepted(students):
    students["Math"] = students["Math"].astype(str)  # "90", "80", ...
    out = analysis.calculate_results(students, SUBJECTS)
    assert row(out, "Asha")["Total_Marks"] == 285


# ---------------------------------------------------------------------------
# 9-10. Marks below zero / above 100
# ---------------------------------------------------------------------------
def test_marks_below_zero(students):
    students.loc[1, "English"] = -5
    report = analysis.validate_marks(students, SUBJECTS)
    assert report.out_of_range == {"English": [1]}
    with pytest.raises(analysis.ValidationError, match="outside the valid range"):
        analysis.calculate_results(students, SUBJECTS)


def test_marks_above_100(students):
    students.loc[0, "Science"] = 105
    report = analysis.validate_marks(students, SUBJECTS)
    assert report.out_of_range == {"Science": [0]}
    with pytest.raises(analysis.ValidationError, match="outside the valid range"):
        analysis.calculate_results(students, SUBJECTS)


def test_zero_and_hundred_are_valid():
    df = pd.DataFrame({"Math": [0, 100], "English": [100, 0]})
    assert analysis.validate_marks(df, ["Math", "English"]).is_valid


# ---------------------------------------------------------------------------
# 11. Empty dataset
# ---------------------------------------------------------------------------
def test_empty_dataframe():
    empty = pd.DataFrame(columns=["Name", "Math"])
    report = analysis.validate_marks(empty, ["Math"])
    assert not report.is_valid
    assert "empty" in report.errors[0].lower()
    with pytest.raises(analysis.ValidationError, match="empty"):
        analysis.calculate_results(empty, ["Math"])


def test_empty_csv_files_are_rejected():
    with pytest.raises(analysis.ValidationError):
        analysis.load_csv(io.StringIO(""))  # completely empty file
    with pytest.raises(analysis.ValidationError):
        analysis.load_csv(io.StringIO("Name,Math\n"))  # header only, no students


# ---------------------------------------------------------------------------
# 12. Missing marks (never treated as zero)
# ---------------------------------------------------------------------------
def test_missing_marks_are_reported(students):
    students.loc[3, "English"] = None
    report = analysis.validate_marks(students, SUBJECTS)
    assert report.missing_values == {"English": [3]}
    with pytest.raises(analysis.ValidationError, match="missing"):
        analysis.calculate_results(students, SUBJECTS)


def test_blank_text_counts_as_missing():
    df = pd.DataFrame({"Math": ["80", "  "], "English": ["70", "60"]})
    report = analysis.validate_marks(df, ["Math", "English"])
    assert report.missing_values == {"Math": [1]}
    assert report.non_numeric == {}


def test_missing_marks_are_not_treated_as_zero(students):
    """Leaving out a problem row must not change anyone else's result."""
    expected = analysis.calculate_results(students, SUBJECTS)

    broken = students.copy()
    broken.loc[3, "English"] = None  # Dev
    good, problem = analysis.split_valid_and_problem_rows(broken, SUBJECTS)

    assert problem["Name"].tolist() == ["Dev"]  # the problem row is returned, not hidden
    assert "Dev" not in good["Name"].tolist()
    out = analysis.calculate_results(good, SUBJECTS)
    assert len(out) == len(students) - 1
    expected_without_dev = expected[expected["Name"] != "Dev"].reset_index(drop=True)
    # check_dtype=False: a column that once held a missing value is stored as decimals (95.0 instead of 95).
    pd.testing.assert_frame_equal(out.reset_index(drop=True), expected_without_dev, check_dtype=False)


# ---------------------------------------------------------------------------
# 13. Filtering (grade, pass/fail, search)
# ---------------------------------------------------------------------------
def test_filter_by_grade(results):
    only_a_plus = analysis.filter_results(results, grades=["A+"])
    assert only_a_plus["Name"].tolist() == ["Asha"]

    a_or_b = analysis.filter_results(results, grades=["A", "B"])
    assert sorted(a_or_b["Name"]) == ["Ben", "Dev"]


def test_filter_by_pass_fail(results):
    failed = analysis.filter_results(results, statuses=["Fail"])
    assert failed["Name"].tolist() == ["Dev"]
    passed = analysis.filter_results(results, statuses=["Pass"])
    assert len(passed) == 5


def test_filter_grade_and_status_together(results):
    out = analysis.filter_results(results, grades=["B"], statuses=["Pass"])
    assert out.empty  # the only B student (Dev) failed


def test_no_filter_returns_everyone(results):
    assert len(analysis.filter_results(results)) == len(results)
    assert len(analysis.filter_results(results, grades=[], statuses=[])) == len(results)


def test_search_by_name_and_id(results):
    columns = analysis.find_search_columns(results)
    assert columns == ["Student_ID", "Name"]
    by_name = analysis.filter_results(results, search_text="chit", search_columns=columns)
    assert by_name["Name"].tolist() == ["Chitra"]
    by_id = analysis.filter_results(results, search_text="s5", search_columns=columns)  # case-insensitive
    assert by_id["Name"].tolist() == ["Esha"]
    nobody = analysis.filter_results(results, search_text="zzz", search_columns=columns)
    assert nobody.empty


def test_search_when_no_id_or_name_column_exists():
    df = pd.DataFrame({"Math": [50, 60], "English": [70, 80]})
    out = analysis.calculate_results(df, ["Math", "English"])
    assert analysis.find_search_columns(out) == []
    # Search text is ignored (not an error) when there is nothing to search in.
    assert len(analysis.filter_results(out, search_text="abc", search_columns=[])) == 2


# ---------------------------------------------------------------------------
# 14. CSV export
# ---------------------------------------------------------------------------
def test_csv_export_columns_and_values(students, results):
    csv_bytes = analysis.results_to_csv(results)
    exported = pd.read_csv(io.BytesIO(csv_bytes))

    # Original student columns first, then the calculated columns.
    assert list(exported.columns) == list(students.columns) + analysis.RESULT_COLUMNS
    assert len(exported) == len(students)
    assert exported["Name"].tolist() == students["Name"].tolist()
    assert exported["Math"].tolist() == students["Math"].tolist()
    assert exported["Grade"].tolist() == results["Grade"].tolist()
    assert exported["Result"].tolist() == results["Result"].tolist()
    assert "Unnamed: 0" not in exported.columns  # no stray index column


def test_csv_export_keeps_extra_original_columns(students):
    students["Gender"] = ["F", "M", "F", "M", "F", "M"]
    out = analysis.calculate_results(students, SUBJECTS)
    exported = pd.read_csv(io.BytesIO(analysis.results_to_csv(out)))
    assert "Gender" in exported.columns
    assert exported["Gender"].tolist() == students["Gender"].tolist()


# ---------------------------------------------------------------------------
# Extra tests: summary, chart data, column name clashes, the sample file
# ---------------------------------------------------------------------------
def test_summary(results):
    summary = analysis.summarize_results(results)
    assert summary["total_students"] == 6
    assert summary["passed"] == 5
    assert summary["failed"] == 1
    # (95 + 80 + 65 + 71.67 + 45 + 55) / 6 = 68.6116...
    assert summary["class_average_percentage"] == pytest.approx(68.61, abs=0.01)
    assert summary["highest_percentage"] == pytest.approx(95.0)
    assert summary["lowest_percentage"] == pytest.approx(45.0)


def test_summary_of_empty_results(results):
    summary = analysis.summarize_results(results.iloc[0:0])
    assert summary["total_students"] == 0
    assert summary["class_average_percentage"] is None


def test_chart_data(students, results):
    averages = analysis.subject_averages(results, SUBJECTS)
    assert averages["Math"] == pytest.approx(students["Math"].mean(), abs=0.01)

    grades = analysis.grade_distribution(results)
    assert grades.to_dict() == {"A+": 1, "A": 1, "B": 1, "C": 1, "D": 1, "F": 1}
    assert list(grades.index) == analysis.GRADE_ORDER  # all grades listed, in order

    pass_fail = analysis.pass_fail_distribution(results)
    assert pass_fail.to_dict() == {"Pass": 5, "Fail": 1}


def test_existing_columns_are_never_overwritten(students):
    students["Grade"] = ["old"] * len(students)
    out = analysis.calculate_results(students, SUBJECTS)
    assert out["Grade"].tolist() == ["old"] * len(students)  # the user's column is untouched
    assert "Calculated_Grade" in out.columns
    names = analysis.result_column_names(out, list(students.columns))
    assert names["Grade"] == "Calculated_Grade"
    assert names["Result"] == "Result"


def test_suggest_subject_columns(students):
    assert analysis.suggest_subject_columns(students) == SUBJECTS


def test_suggest_keeps_marks_column_that_has_a_typo(students):
    """A marks column with one typo must still be suggested, so the typo gets reported."""
    students["Math"] = students["Math"].astype(object)
    students.loc[2, "Math"] = "abc"
    suggested = analysis.suggest_subject_columns(students)
    assert suggested == SUBJECTS
    assert analysis.validate_marks(students, suggested).non_numeric == {"Math": [2]}


def test_suggest_ignores_text_columns():
    df = pd.DataFrame({"Name": ["A", "B"], "Gender": ["F", "M"], "Math": [50, 60], "Notes": ["", ""]})
    assert analysis.suggest_subject_columns(df) == ["Math"]


def test_sample_dataset_works():
    """The included sample file must be valid and show every grade and both outcomes."""
    sample = analysis.load_csv(PROJECT_FOLDER / "sample_students.csv")
    subjects = ["Mathematics", "English", "Science", "Computer"]

    assert len(sample) >= 30
    assert analysis.suggest_subject_columns(sample) == subjects
    assert analysis.validate_marks(sample, subjects).is_valid
    assert (sample["Data_Type"] == "Fictional demo data").all()

    out = analysis.calculate_results(sample, subjects)

    # Every grade and both Pass and Fail appear.
    assert set(out["Grade"]) == set(analysis.GRADE_ORDER)
    assert set(out["Result"]) == {"Pass", "Fail"}

    # Re-calculate every percentage in a completely separate way and compare.
    for _, student in out.iterrows():
        marks = [student[s] for s in subjects]
        assert student["Total_Marks"] == sum(marks)
        assert student["Percentage"] == pytest.approx(sum(marks) / 4, abs=0.01)
        assert (student["Result"] == "Pass") == all(m >= 40 for m in marks)

    # Spot-check a few known students.
    assert row(out, "Simran Kaur")["Grade"] == "A+"  # exactly 90 percent
    assert row(out, "Karan Thakur")["Result"] == "Fail"  # 38 in English
    assert row(out, "Ayaan Khan")["Result"] == "Pass"  # exactly 40 in every subject
    assert row(out, "Neha Tiwari")["Grade"] == "F"


def test_load_csv_handles_excel_bom():
    """Excel's 'CSV UTF-8' adds a hidden marker at the start; it must not end up in a column name."""
    data = io.BytesIO("Student_ID,Name,Math\nS1,Asha,90\n".encode("utf-8-sig"))
    assert list(analysis.load_csv(data).columns) == ["Student_ID", "Name", "Math"]


def test_load_csv_can_be_read_twice_from_the_same_file_object():
    """Streamlit re-runs the script on every click, so the same upload is read many times."""
    data = io.BytesIO(b"Name,Math\nAsha,90\n")
    first = analysis.load_csv(data)
    second = analysis.load_csv(data)
    pd.testing.assert_frame_equal(first, second)


def test_load_csv_rejects_wrong_encoding_with_helpful_message():
    data = io.BytesIO("Name,Math\nJosé,90\n".encode("cp1252"))  # not valid UTF-8
    with pytest.raises(analysis.ValidationError, match="UTF-8"):
        analysis.load_csv(data)


def test_load_csv_rejects_semicolon_separated_file_with_helpful_message():
    with pytest.raises(analysis.ValidationError, match="semicolons"):
        analysis.load_csv(io.BytesIO(b"Name;Math;English\nAsha;90;80\n"))


def test_load_csv_strips_column_name_spaces():
    df = analysis.load_csv(io.StringIO(" Name , Math \nAsha,90\n"))
    assert list(df.columns) == ["Name", "Math"]


# ===========================================================================
# Search and filter regression tests
# ===========================================================================
# A small class where the correct answer for every search can be worked out by hand.
#
#   ID   Name            Math Sci Eng   Percentage  Grade  Result
#    1   Jamie Jones      75   72  78     75.00      B     Pass
#    2   Jamie Jones     100  100  38     79.33      B     Fail   (38 is below 40)
#   14   Jamie Smith      82   85  88     85.00      A     Pass
#  114   Jamie Lee        50   30  60     46.67      F     Fail
#  140   Alex Brown       95   92  98     95.00      A+    Pass
#   15   priya nair       66   64  70     66.67      C     Pass   (stored in lower case)
#   16     Rahul   Das    55   52  58     55.00      D     Pass   (extra spaces stored in the name)
#   17   Sana Khan        45   48  44     45.67      F     Pass
SEARCH_SUBJECTS = ["Math", "Sci", "Eng"]


@pytest.fixture
def class_list():
    raw = pd.DataFrame(
        {
            "Student_ID": [1, 2, 14, 114, 140, 15, 16, 17],
            "Name": ["Jamie Jones", "Jamie Jones", "Jamie Smith", "Jamie Lee", "Alex Brown",
                     "priya nair", "  Rahul   Das  ", "Sana Khan"],
            "Math": [75, 100, 82, 50, 95, 66, 55, 45],
            "Sci": [72, 100, 85, 30, 92, 64, 52, 48],
            "Eng": [78, 38, 88, 60, 98, 70, 58, 44],
        }
    )
    return analysis.calculate_results(raw, SEARCH_SUBJECTS)


def ids(table):
    """The Student_ID values of a result table, as a plain list."""
    return table["Student_ID"].tolist()


def find(table, **kwargs):
    return analysis.filter_results(table, search_columns=analysis.find_search_columns(table), **kwargs)


def test_fixture_has_the_grades_and_results_the_comments_promise(class_list):
    """If this fails, the expected values in the tests below would be wrong."""
    expected = {1: ("B", "Pass"), 2: ("B", "Fail"), 14: ("A", "Pass"), 114: ("F", "Fail"),
                140: ("A+", "Pass"), 15: ("C", "Pass"), 16: ("D", "Pass"), 17: ("F", "Pass")}
    actual = {r.Student_ID: (r.Grade, r.Result) for r in class_list.itertuples()}
    assert actual == expected


# 1. exact name
def test_search_by_exact_name(class_list):
    assert ids(find(class_list, search_text="Jamie Jones")) == [1, 2]
    assert ids(find(class_list, search_text="Alex Brown")) == [140]


# 2. partial name
def test_search_by_partial_name(class_list):
    assert ids(find(class_list, search_text="jamie")) == [1, 2, 14, 114]
    assert ids(find(class_list, search_text="ones")) == [1, 2]
    assert ids(find(class_list, search_text="Jamie J")) == [1, 2]


# 3. case-insensitive
def test_name_search_ignores_capital_letters(class_list):
    assert ids(find(class_list, search_text="JAMIE jones")) == [1, 2]
    assert ids(find(class_list, search_text="alex BROWN")) == [140]
    assert ids(find(class_list, search_text="PRIYA")) == [15]  # stored in lower case


# 4. ID search
def test_search_by_student_id_is_exact(class_list):
    assert ids(find(class_list, search_text="14")) == [14]  # NOT 114, 140
    assert ids(find(class_list, search_text="114")) == [114]
    assert ids(find(class_list, search_text="140")) == [140]
    assert ids(find(class_list, search_text="1")) == [1]  # NOT 14, 114, 140, 15, 16, 17


def test_id_search_works_for_numeric_float_and_text_ids():
    marks = pd.DataFrame({"Math": [50, 60, 70, 80]})
    for id_values in ([1, 14, 114, 140], [1.0, 14.0, 114.0, 140.0], ["1", "14", "114", "140"], ["1", "14.0", "114", "140"]):
        table = analysis.calculate_results(marks.assign(Student_ID=id_values), ["Math"])
        assert ids(find(table, search_text="14")) == [id_values[1]]

    text_ids = analysis.calculate_results(
        pd.DataFrame({"Student_ID": ["S01", "S010", "s011"], "Math": [50, 60, 70]}), ["Math"]
    )
    assert ids(find(text_ids, search_text="s01")) == ["S01"]  # whole ID only
    assert ids(find(text_ids, search_text="S011")) == ["s011"]  # case-insensitive


def test_float_ids_caused_by_a_missing_id_still_match():
    """A missing ID turns the whole column into decimals (14.0). Searching "14" must still work."""
    table = analysis.calculate_results(
        pd.DataFrame({"Student_ID": [1, None, 14], "Math": [50, 60, 70]}), ["Math"]
    )
    assert table["Student_ID"].dtype == float
    assert table[analysis.search_mask(table, "14", ["Student_ID"])]["Math"].tolist() == [70]


# 5. leading/trailing spaces
def test_search_ignores_spaces_around_the_text(class_list):
    assert ids(find(class_list, search_text="  jamie jones  ")) == [1, 2]
    assert ids(find(class_list, search_text="\t14 \n")) == [14]
    assert ids(find(class_list, search_text="jamie    jones")) == [1, 2]  # repeated spaces inside


def test_search_ignores_extra_spaces_stored_in_the_data(class_list):
    assert ids(find(class_list, search_text="rahul das")) == [16]


# 6. grade filter
def test_grade_b_filter_returns_only_grade_b(class_list):
    out = find(class_list, grades=["B"])
    assert ids(out) == [1, 2]
    assert set(out["Grade"]) == {"B"}


@pytest.mark.parametrize(
    "grade, expected_ids",
    [("A+", [140]), ("A", [14]), ("B", [1, 2]), ("C", [15]), ("D", [16]), ("F", [114, 17])],
)
def test_every_grade_filter(class_list, grade, expected_ids):
    assert sorted(ids(find(class_list, grades=[grade]))) == sorted(expected_ids)


# 7-8. pass / fail
def test_pass_only_filter(class_list):
    out = find(class_list, statuses=["Pass"])
    assert ids(out) == [1, 14, 140, 15, 16, 17]
    assert set(out["Result"]) == {"Pass"}


def test_fail_only_filter(class_list):
    out = find(class_list, statuses=["Fail"])
    assert ids(out) == [2, 114]
    assert set(out["Result"]) == {"Fail"}


def test_pass_and_fail_selected_together_shows_both(class_list):
    assert len(find(class_list, statuses=["Pass", "Fail"])) == len(class_list)


def test_pass_fail_filter_uses_the_pass_mark_of_the_calculation():
    """The filter must follow the app's pass mark, not a hard-coded 40."""
    df = pd.DataFrame({"Student_ID": [1, 2], "Math": [45, 55]})
    strict = analysis.calculate_results(df, ["Math"], pass_mark=50)
    assert ids(find(strict, statuses=["Pass"])) == [2]
    assert ids(find(strict, statuses=["Fail"])) == [1]


# 9-10. combined filters (logical AND)
def test_combined_name_grade_and_pass(class_list):
    out = find(class_list, search_text="Jamie Jones", grades=["B"], statuses=["Pass"])
    assert ids(out) == [1]
    row_1 = out.iloc[0]
    assert (row_1["Name"], row_1["Grade"], row_1["Result"]) == ("Jamie Jones", "B", "Pass")


def test_combined_name_grade_and_fail_finds_the_other_jamie_jones(class_list):
    assert ids(find(class_list, search_text="Jamie Jones", grades=["B"], statuses=["Fail"])) == [2]


def test_combined_partial_name_grade_and_pass(class_list):
    # "jamie" matches 1, 2, 14, 114; grade B keeps 1, 2; Pass keeps 1.
    assert ids(find(class_list, search_text="jamie", grades=["B"], statuses=["Pass"])) == [1]


def test_combined_id_grade_and_fail(class_list):
    assert ids(find(class_list, search_text="114", grades=["F"], statuses=["Fail"])) == [114]
    assert find(class_list, search_text="114", grades=["B"], statuses=["Fail"]).empty  # wrong grade
    assert find(class_list, search_text="114", grades=["F"], statuses=["Pass"]).empty  # wrong result


def test_conditions_are_and_not_or(class_list):
    """With OR logic these would return many students; with AND exactly one or none."""
    assert ids(find(class_list, search_text="alex", grades=["A+"], statuses=["Pass"])) == [140]
    assert find(class_list, search_text="alex", grades=["F"], statuses=["Fail"]).empty


# 11. empty search with active filters
def test_empty_search_keeps_the_other_filters(class_list):
    assert ids(find(class_list, search_text="", grades=["B"], statuses=["Pass"])) == [1]
    assert ids(find(class_list, search_text="   ", grades=["B"], statuses=["Pass"])) == [1]
    assert ids(find(class_list, search_text=None, statuses=["Fail"])) == [2, 114]


def test_no_search_and_no_filters_returns_everyone(class_list):
    assert ids(find(class_list)) == ids(class_list)


# 12. no matching results
def test_no_match_returns_an_empty_table_never_everyone(class_list):
    out = find(class_list, search_text="nobody here")
    assert out.empty
    assert list(out.columns) == list(class_list.columns)  # still a proper (empty) results table
    assert find(class_list, search_text="999").empty  # unknown ID
    assert find(class_list, search_text="1400").empty


def test_empty_state_messages(class_list):
    cols = analysis.find_search_columns(class_list)
    nothing = analysis.describe_empty_result(class_list, "nobody here", cols)
    assert nothing == "No students found matching your search."

    filtered_out = analysis.describe_empty_result(class_list, "alex", cols, grades=["F"])
    assert "1 student(s) match your search, but none of them also satisfy" in filtered_out

    only_filters = analysis.describe_empty_result(class_list, "", cols, grades=["A+"], statuses=["Fail"])
    assert only_filters == "No students satisfy the selected Grade / Pass-Fail filters."

    assert analysis.describe_empty_result(class_list, "jamie", cols) == ""  # something matched -> no message


# 13. clearing one filter keeps the others
def test_clearing_one_condition_removes_only_that_condition(class_list):
    everything = dict(search_text="jamie", grades=["B"], statuses=["Pass"])
    assert ids(find(class_list, **everything)) == [1]
    assert ids(find(class_list, **{**everything, "grades": []})) == [1, 14]  # grade cleared
    assert ids(find(class_list, **{**everything, "statuses": []})) == [1, 2]  # Pass/Fail cleared
    assert ids(find(class_list, **{**everything, "search_text": ""})) == [1]  # search cleared (only 1 is B+Pass)
    assert ids(find(class_list, search_text="", grades=["A", "B"], statuses=["Pass"])) == [1, 14]


# 14. several grades at once
def test_multiple_selected_grades(class_list):
    assert ids(find(class_list, grades=["A+", "A"])) == [14, 140]
    assert ids(find(class_list, grades=["B", "F"], statuses=["Fail"])) == [2, 114]
    assert ids(find(class_list, search_text="jamie", grades=["A", "F"])) == [14, 114]


# 15. missing names, IDs, grades and results
@pytest.fixture
def messy(class_list):
    table = class_list.copy()
    table["Name"] = table["Name"].astype(object)
    table.loc[table.Student_ID == 1, "Name"] = None  # no name
    table["Student_ID"] = table["Student_ID"].astype(float)
    table.loc[table.Student_ID == 14, "Student_ID"] = None  # no ID
    table["Grade"] = table["Grade"].astype(object)
    table.loc[table.Student_ID == 140, "Grade"] = None  # no grade
    table["Result"] = table["Result"].astype(object)
    table.loc[table.Student_ID == 15, "Result"] = None  # no result
    return table


def test_missing_names_do_not_crash_or_match(messy):
    out = find(messy, search_text="jamie")
    assert out["Math"].tolist() == [100, 82, 50]  # the row without a name (Math 75) is not found
    assert find(messy, search_text="nan").empty  # a missing name is NOT the text "nan"
    assert find(messy, search_text="none").empty


def test_missing_ids_do_not_match_any_id_search(messy):
    assert messy["Student_ID"].isna().sum() == 1
    assert find(messy, search_text="14").empty  # ID 14 was made missing
    assert find(messy, search_text="nan").empty
    assert messy.loc[find(messy, search_text="114").index, "Math"].tolist() == [50]


def test_missing_grade_or_result_is_excluded_only_when_that_filter_is_active(messy):
    assert len(find(messy)) == len(messy)  # nothing active: everyone, including the incomplete rows
    # Alex Brown (grade removed) is not found by any grade filter ...
    assert 140 not in messy.loc[find(messy, grades=analysis.GRADE_ORDER).index, "Student_ID"].tolist()
    assert len(find(messy, grades=analysis.GRADE_ORDER)) == len(messy) - 1
    # ... but is found by search + Pass filter, because only the grade is missing.
    assert find(messy, search_text="alex", statuses=["Pass"])["Math"].tolist() == [95]
    # Priya (result removed) is not found by a Pass/Fail filter.
    assert find(messy, search_text="priya", statuses=["Pass", "Fail"]).empty
    assert find(messy, search_text="priya")["Math"].tolist() == [66]


# 16. filtering after uploading a different CSV
def test_filtering_uses_the_current_file_not_the_previous_one():
    first = analysis.load_csv(PROJECT_FOLDER / "sample_students.csv")
    first_results = analysis.calculate_results(first, ["Mathematics", "English", "Science", "Computer"])
    second = analysis.load_csv(
        io.StringIO("Roll_No,Student Name,Maths,Physics\n7,Jamie Quinn,88,91\n8,Omar Reyes,35,70\n")
    )
    second_results = analysis.calculate_results(second, ["Maths", "Physics"])

    # A student of the first file is searched for in the second file: not there.
    assert find(first_results, search_text="Aarav Sharma")["Name"].tolist() == ["Aarav Sharma"]
    assert find(second_results, search_text="Aarav Sharma").empty
    # The second file has its own ID/name column names and its own students.
    assert analysis.find_search_columns(second_results) == ["Roll_No", "Student Name"]
    out = find(second_results, search_text="jamie", grades=["A"], statuses=["Pass"])
    assert out["Student Name"].tolist() == ["Jamie Quinn"]
    assert find(second_results, statuses=["Fail"])["Student Name"].tolist() == ["Omar Reyes"]
    assert len(find(second_results)) == 2  # never the 36 students of the first file


# 17. full details of a unique match
def test_student_details_of_a_unique_match(class_list):
    match = find(class_list, search_text="14")
    assert len(match) == 1
    details = analysis.student_details_table(match.iloc[0])

    assert list(details.columns) == ["Field", "Value"]
    assert details["Field"].tolist() == list(class_list.columns)  # every real column, same order
    shown = dict(zip(details["Field"], details["Value"]))
    assert shown == {
        "Student_ID": "14", "Name": "Jamie Smith", "Math": "82", "Sci": "85", "Eng": "88",
        "Total_Marks": "255", "Average_Marks": "85", "Percentage": "85", "Grade": "A", "Result": "Pass",
    }


def test_student_details_show_missing_values_and_decimals_honestly(messy):
    row = messy[messy["Math"] == 75].iloc[0]  # the student whose name was removed
    shown = dict(zip(*analysis.student_details_table(row).T.values))
    assert shown["Name"] == "(missing)"
    assert shown["Student_ID"] == "1"
    assert shown["Percentage"] == "75"

    row_15 = messy[messy["Math"] == 66].iloc[0]
    shown_15 = dict(zip(*analysis.student_details_table(row_15).T.values))
    assert shown_15["Result"] == "(missing)"
    assert shown_15["Percentage"] == "66.67"


def test_student_details_use_only_columns_that_exist():
    df = pd.DataFrame({"Name": ["Asha"], "Math": [80], "Age": [19]})
    row = analysis.calculate_results(df, ["Math"]).iloc[0]
    fields = analysis.student_details_table(row)["Field"].tolist()
    assert fields == ["Name", "Math", "Age"] + analysis.RESULT_COLUMNS
    assert "Gender" not in fields and "Attendance" not in fields  # nothing invented


# 18. result counts after filtering
def test_summary_counts_follow_the_filtered_rows(class_list):
    everyone = analysis.summarize_results(class_list)
    assert (everyone["total_students"], everyone["passed"], everyone["failed"]) == (8, 6, 2)

    jamies = analysis.summarize_results(find(class_list, search_text="jamie"))
    assert (jamies["total_students"], jamies["passed"], jamies["failed"]) == (4, 2, 2)
    # (75 + 79.33 + 85 + 46.67) / 4 = 71.5
    assert jamies["class_average_percentage"] == pytest.approx(71.5, abs=0.01)
    assert jamies["highest_percentage"] == pytest.approx(85.0)
    assert jamies["lowest_percentage"] == pytest.approx(46.67)

    one = analysis.summarize_results(find(class_list, search_text="jamie jones", grades=["B"], statuses=["Pass"]))
    assert (one["total_students"], one["passed"], one["failed"]) == (1, 1, 0)

    none = analysis.summarize_results(find(class_list, search_text="nobody"))
    assert none["total_students"] == 0 and none["class_average_percentage"] is None


def test_chart_data_follows_the_filtered_rows(class_list):
    jamies = find(class_list, search_text="jamie")
    assert analysis.grade_distribution(jamies).to_dict() == {"A+": 0, "A": 1, "B": 2, "C": 0, "D": 0, "F": 1}
    assert analysis.pass_fail_distribution(jamies).to_dict() == {"Pass": 2, "Fail": 2}
    # Math marks of the four Jamies: 75, 100, 82, 50
    assert analysis.subject_averages(jamies, SEARCH_SUBJECTS)["Math"] == pytest.approx(76.75)


def test_filtered_export_contains_only_the_matching_rows(class_list):
    out = find(class_list, search_text="jamie", grades=["B"])
    exported = pd.read_csv(io.BytesIO(analysis.results_to_csv(out)))
    assert exported["Student_ID"].tolist() == [1, 2]
    assert list(exported.columns) == list(class_list.columns)


# missing-value counts: whole file vs filtered rows
def test_missing_cell_counts_for_whole_file_and_for_filtered_rows():
    df = pd.DataFrame(
        {
            "Student_ID": [1, 2, 3],
            "Name": ["Asha", "Ben", "Chitra"],
            "Math": [80, 70, 60],
            "Age": [19.0, None, None],
            "Attendance": [None, None, 90.0],
        }
    )
    results = analysis.calculate_results(df, ["Math"])
    original = list(df.columns)
    assert analysis.count_missing_cells(df) == 4  # whole file
    assert analysis.count_missing_cells(results, original) == 4  # calculated columns add no gaps
    ben = find(results, search_text="ben")
    assert analysis.count_missing_cells(ben, original) == 2
    asha = find(results, search_text="asha")
    assert analysis.count_missing_cells(asha, original) == 1
    assert analysis.count_missing_cells(find(results, search_text="nobody"), original) == 0


# ---------------------------------------------------------------------------
# Helpers around search: column detection, input is never changed, column clashes
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "columns, expected",
    [
        (["Student_ID", "Name", "Math"], ["Student_ID", "Name"]),
        (["Student ID", "Student Name", "Math"], ["Student ID", "Student Name"]),
        (["StudentID", "FullName", "Math"], ["StudentID", "FullName"]),
        (["ID", "Roll No", "Math"], ["ID", "Roll No"]),
        (["Math", "Science", "Attendance", "Valid", "Hybrid", "Paid"], []),  # words that merely end in "id"
    ],
)
def test_find_search_columns(columns, expected):
    assert analysis.find_search_columns(pd.DataFrame(columns=columns)) == expected


def test_filter_does_not_change_the_input_table(class_list):
    before = class_list.copy()
    find(class_list, search_text="jamie", grades=["B"], statuses=["Pass"])
    pd.testing.assert_frame_equal(class_list, before)


def test_filter_returns_an_independent_copy(class_list):
    out = find(class_list, search_text="jamie")
    out.loc[out.index[0], "Math"] = -999
    assert -999 not in class_list["Math"].tolist()


def test_search_without_id_or_name_columns_is_ignored():
    table = analysis.calculate_results(pd.DataFrame({"Math": [50, 60]}), ["Math"])
    assert len(analysis.filter_results(table, search_text="anything", search_columns=[])) == 2


def test_name_and_id_columns_are_both_searched():
    table = analysis.calculate_results(
        pd.DataFrame({"Student_ID": [7, 8], "Name": ["Student 8", "Ravi"], "Math": [50, 60]}), ["Math"]
    )
    # "8" is the ID of Ravi and also part of the name "Student 8": both are legitimate matches.
    assert sorted(find(table, search_text="8")["Math"].tolist()) == [50, 60]


def test_existing_grade_and_result_columns_are_kept_and_filters_use_the_calculated_ones():
    """A file that already has Grade/Result columns: its own values stay, filters use the app's."""
    df = pd.DataFrame(
        {"Student_ID": [1, 2], "Name": ["Asha", "Ben"], "Math": [95, 45], "Grade": ["X", "Y"], "Result": ["?", "?"]}
    )
    assert analysis.result_column_clashes(df) == ["Grade", "Result"]
    results = analysis.calculate_results(df, ["Math"])
    names = analysis.result_column_names(results, list(df.columns))
    assert names["Grade"] == "Calculated_Grade" and names["Result"] == "Calculated_Result"
    assert results["Grade"].tolist() == ["X", "Y"]  # the file's own column is untouched
    out = analysis.filter_results(
        results, grades=["A+"], grade_column=names["Grade"], result_column=names["Result"]
    )
    assert out["Name"].tolist() == ["Asha"]


def test_subject_suggestion_skips_columns_that_are_not_marks():
    df = pd.DataFrame(
        {
            "Student_ID": [1, 2], "Name": ["A", "B"], "Age": [19, 20], "Gender": ["F", "M"],
            "Quiz 1": [8, 9], "Quiz2": [7, 6], "Total_Assignments": [10, 10], "Assignments_Submitted": [9, 8],
            "Midterm": [60, 70], "Final": [65, 75], "Attendance": [90, 80], "Total": [100, 110],
            "Percentage": [60.5, 70.5], "Grade": ["B", "A"], "Result": ["Pass", "Pass"],
        }
    )
    assert analysis.suggest_subject_columns(df) == ["Quiz 1", "Quiz2", "Midterm", "Final"]
