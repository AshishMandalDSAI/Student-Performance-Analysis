"""Student Performance Analysis System - Streamlit user interface.

This file only handles what the user sees. All calculations and checks
are done by functions in analysis.py.

Run with:  python -m streamlit run app.py
"""

import hashlib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw charts in memory (no pop-up windows)
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import analysis  # noqa: E402

SAMPLE_FILE = Path(__file__).parent / "sample_students.csv"

st.set_page_config(page_title="Student Performance Analysis System", page_icon="📊", layout="wide")


# ---------------------------------------------------------------------------
# Small helper functions used only by the interface
# ---------------------------------------------------------------------------
def choose_label_column(df: pd.DataFrame):
    """Pick the column used to label students in charts: a name column, else an ID column."""
    candidates = analysis.find_search_columns(df)
    for col in candidates:
        if "name" in str(col).lower():
            return col
    return candidates[0] if candidates else None


def show_chart(fig):
    """Display a Matplotlib figure and free its memory."""
    st.pyplot(fig)
    plt.close(fig)


def add_bar_labels(ax, bars, fmt="{:g}"):
    """Write the value on top of each bar."""
    for bar in bars:
        ax.annotate(
            fmt.format(bar.get_height()),
            (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            ha="center",
            va="bottom",
            fontsize=9,
        )


# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------
st.title("📊 Student Performance Analysis System")
st.write(
    "This application reads a CSV file of student marks and calculates each student's "
    "**total, average, percentage, grade and Pass/Fail result**. It then shows a class summary, "
    "simple charts, and lets you search, filter and download the results. "
    "It uses only basic calculations - no AI, no machine learning, no database."
)

with st.expander("How to use this application", expanded=True):
    st.markdown(
        """
1. In the **sidebar**, upload a CSV file - or tick **Use the sample dataset** to try it out.
2. Check the **dataset preview** and the missing-value information.
3. In the sidebar, choose which columns contain **subject marks**.
4. If the app finds problems in the marks, read the error messages and fix the CSV
   (or choose to leave out the affected rows).
5. View the **summary**, **charts** and the **results table**.
6. Use the sidebar to **search** (type, then press Enter) and **filter** students. The summary, charts and results follow your selection. Then **download** the results as CSV.
        """
    )

# ---------------------------------------------------------------------------
# Sidebar: upload
# ---------------------------------------------------------------------------
st.sidebar.header("1. Upload data")
uploaded = st.sidebar.file_uploader("Upload a CSV file", type=["csv"])
use_sample = st.sidebar.checkbox(
    "Use the sample dataset (fictional)",
    value=False,
    help="Loads sample_students.csv, which contains 36 fictional students.",
)

if uploaded is None and not use_sample:
    st.info("👈 Upload a CSV file or tick **Use the sample dataset** in the sidebar to begin.")
    st.stop()

# ---------------------------------------------------------------------------
# Load the data
# ---------------------------------------------------------------------------
try:
    if uploaded is not None:
        df = analysis.load_csv(uploaded)
        data_key = f"{uploaded.name}-{hashlib.md5(uploaded.getvalue()).hexdigest()[:10]}"
        st.caption(f"Using uploaded file: **{uploaded.name}**")
    else:
        df = analysis.load_csv(SAMPLE_FILE)
        data_key = "sample"
        st.caption("Using the included sample dataset. ⚠️ All names and marks in it are **fictional demonstration data**.")
except analysis.ValidationError as error:
    st.error(f"❌ {error}")
    st.stop()
except FileNotFoundError:
    st.error("❌ The sample file sample_students.csv was not found next to app.py.")
    st.stop()

# ---------------------------------------------------------------------------
# Dataset preview
# ---------------------------------------------------------------------------
st.header("Dataset preview")
col_rows, col_cols = st.columns(2)
col_rows.metric("Number of rows", len(df))
col_cols.metric("Number of columns", len(df.columns))

st.write("**Column names:** " + ", ".join(f"`{c}`" for c in df.columns))
st.dataframe(df, width="stretch")

st.subheader("Missing values (complete uploaded dataset)")
missing_counts = df.isna().sum()
if missing_counts.sum() == 0:
    st.success("No missing values were found in the complete uploaded dataset.")
else:
    missing_table = pd.DataFrame(
        {
            "Column": missing_counts.index,
            "Missing cells": missing_counts.values,
            "Missing %": (missing_counts.values / len(df) * 100).round(1),
        }
    )
    st.warning(
        f"The complete uploaded dataset ({len(df)} rows) has {int(missing_counts.sum())} missing cell(s) in total. "
        "This count covers every row, before any search or filter."
    )
    st.dataframe(missing_table[missing_table["Missing cells"] > 0], hide_index=True, width="stretch")

# ---------------------------------------------------------------------------
# Sidebar: choose marks columns and settings
# ---------------------------------------------------------------------------
st.sidebar.header("2. Choose subject columns")
subject_columns = st.sidebar.multiselect(
    "Columns that contain subject marks",
    options=list(df.columns),
    default=analysis.suggest_subject_columns(df),
    key=f"subjects-{data_key}",
    help="Select every column that holds marks for one subject.",
)

with st.sidebar.expander("Advanced settings (optional)"):
    max_mark = st.number_input("Maximum marks per subject", min_value=1.0, value=analysis.MAX_MARK, step=1.0)
    pass_mark = st.number_input(
        "Passing marks (needed in EVERY subject)",
        min_value=0.0,
        max_value=float(max_mark),
        value=min(analysis.PASS_MARK, float(max_mark)),
        step=1.0,
    )

# ---------------------------------------------------------------------------
# Data validation
# ---------------------------------------------------------------------------
st.header("Data validation")
st.info(
    f"**Assumption:** marks must be numbers between **{analysis.MIN_MARK:g}** and **{max_mark:g}**. "
    "Missing, non-numeric or out-of-range marks are never treated as zero and are never changed silently."
)

report = analysis.validate_marks(df, subject_columns, analysis.MIN_MARK, max_mark)
data_to_use = df

if report.is_valid:
    st.success("✅ All selected marks are valid.")
else:
    for message in report.errors:
        st.error("❌ " + message)

    if report.problem_rows:
        problem_view = df.iloc[report.problem_rows].copy()
        problem_view.insert(0, "CSV_Line", [pos + 2 for pos in report.problem_rows])  # line 1 is the header
        st.write(f"**{len(report.problem_rows)} row(s) with problems** (CSV_Line is the line number in your file):")
        st.dataframe(problem_view, hide_index=True, width="stretch")

        leave_out = st.checkbox(
            "Leave these rows out of the calculation and continue",
            value=False,
            help="The rows stay in your original file. They are only excluded from the results.",
        )
        if leave_out:
            data_to_use, _ = analysis.split_valid_and_problem_rows(df, subject_columns, analysis.MIN_MARK, max_mark)
            st.warning(
                f"⚠️ {len(report.problem_rows)} row(s) were left out of the results because of invalid marks. "
                f"The results below use the remaining {len(data_to_use)} student(s)."
            )
            if data_to_use.empty:
                st.error("❌ No valid rows are left to calculate. Please fix your CSV file.")
                st.stop()
        else:
            st.info("Fix the problems in your CSV and upload it again, or tick the box above to leave those rows out.")
            st.stop()
    else:
        st.stop()

# ---------------------------------------------------------------------------
# Result calculation
# ---------------------------------------------------------------------------
results = analysis.calculate_results(data_to_use, subject_columns, analysis.MIN_MARK, max_mark, pass_mark)
names = analysis.result_column_names(results, list(data_to_use.columns))

with st.expander("Grading and Pass/Fail rules used"):
    st.markdown(
        f"""
**Percentage** = total marks ÷ (number of subjects × {max_mark:g}) × 100

| Percentage | Grade |
|---|---|
| 90 – 100 | A+ |
| 80 – 89.99 | A |
| 70 – 79.99 | B |
| 60 – 69.99 | C |
| 50 – 59.99 | D |
| Below 50 | F |

**Pass/Fail:** a student **passes** only if they score at least **{pass_mark:g}** in **every** selected subject.
Scoring below {pass_mark:g} in even one subject means **Fail**.

Grade and Pass/Fail are decided separately, so a student can have grade F and still Pass
(for example 45 in every subject), or have a good grade and still Fail (one subject below {pass_mark:g}).
        """
    )

# ---------------------------------------------------------------------------
# Sidebar: search and filter
# ---------------------------------------------------------------------------
# The widget keys contain data_key, so choosing a different file starts with empty
# search/filter boxes instead of keeping the old file's selections.
st.sidebar.header("3. Search and filter")
search_columns = analysis.find_search_columns(data_to_use)
if search_columns:
    search_text = st.sidebar.text_input(
        "Search by student ID or name",
        key=f"search-{data_key}",
        placeholder="e.g. Jamie Jones or 14",
        help=(
            "Type a name or an ID and press Enter. "
            "Names: partial match; capital letters and extra spaces are ignored. "
            "IDs: the whole ID must match (14 finds ID 14, not 114). "
            "Searched columns: " + ", ".join(map(str, search_columns))
        ),
    )
else:
    search_text = ""
    st.sidebar.caption("No ID or name column was found, so searching is not available.")

grade_filter = st.sidebar.multiselect("Filter by grade", options=analysis.GRADE_ORDER, key=f"grades-{data_key}")
status_filter = st.sidebar.multiselect(
    "Filter by Pass / Fail",
    options=[analysis.PASS_LABEL, analysis.FAIL_LABEL],
    key=f"status-{data_key}",
)
st.sidebar.caption("All active search and filter conditions must be true at the same time (AND).")

# Every table, number and chart below uses `filtered`, a fresh copy built from the current file.
filtered = analysis.filter_results(
    results,
    search_text=search_text,
    search_columns=search_columns,
    grades=grade_filter,
    statuses=status_filter,
    grade_column=names["Grade"],
    result_column=names["Result"],
)
searching = bool(search_text.strip()) and bool(search_columns)
filters_active = searching or bool(grade_filter) or bool(status_filter)

if analysis.result_column_clashes(data_to_use):
    st.info(
        "Your file already has column(s) named "
        + ", ".join(f"`{c}`" for c in analysis.result_column_clashes(data_to_use))
        + ". Your own columns are kept unchanged. The app's calculated columns are named "
        + ", ".join(f"`{names[c]}`" for c in analysis.RESULT_COLUMNS)
        + ", and the grade/Pass-Fail filters, summary and charts use the calculated ones."
    )

# ---------------------------------------------------------------------------
# Performance summary
# ---------------------------------------------------------------------------
st.header("Performance summary")
if filters_active:
    st.caption(f"Based on the **{len(filtered)}** of {len(results)} students that match your search/filters.")
else:
    st.caption(f"Based on all {len(results)} students.")

if filtered.empty:
    st.info("There are no matching students to summarise. Change or clear the search/filters in the sidebar.")
else:
    summary = analysis.summarize_results(filtered, names)
    row1 = st.columns(3)
    row1[0].metric("Total students", summary["total_students"])
    row1[1].metric("Passed", summary["passed"])
    row1[2].metric("Failed", summary["failed"])
    row2 = st.columns(3)
    row2[0].metric("Class average percentage", f"{summary['class_average_percentage']:.2f}%")
    row2[1].metric("Highest percentage", f"{summary['highest_percentage']:.2f}%")
    row2[2].metric("Lowest percentage", f"{summary['lowest_percentage']:.2f}%")


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def draw_charts(view: pd.DataFrame):
    """Draw the four charts for the students in `view`."""
    chart_left, chart_right = st.columns(2)

    with chart_left:
        st.subheader("Subject-wise average marks")
        averages = analysis.subject_averages(view, subject_columns)
        fig, ax = plt.subplots(figsize=(6, 4))
        bars = ax.bar(averages.index.astype(str), averages.values, color="#4C78A8")
        add_bar_labels(ax, bars, "{:.1f}")
        ax.set_ylim(0, max_mark)
        ax.set_ylabel("Average marks")
        ax.set_xlabel("Subject")
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
        fig.tight_layout()
        show_chart(fig)

    with chart_right:
        st.subheader("Grade distribution")
        grades = analysis.grade_distribution(view, names["Grade"])
        fig, ax = plt.subplots(figsize=(6, 4))
        bars = ax.bar(grades.index, grades.values, color="#59A14F")
        add_bar_labels(ax, bars, "{:.0f}")
        ax.set_ylabel("Number of students")
        ax.set_xlabel("Grade")
        ax.set_ylim(0, max(grades.max() * 1.15, 1))
        fig.tight_layout()
        show_chart(fig)

    chart_left2, chart_right2 = st.columns(2)

    with chart_left2:
        st.subheader("Pass vs Fail")
        pass_fail = analysis.pass_fail_distribution(view, names["Result"])
        fig, ax = plt.subplots(figsize=(6, 4))
        bars = ax.bar(pass_fail.index, pass_fail.values, color=["#59A14F", "#E15759"])
        add_bar_labels(ax, bars, "{:.0f}")
        ax.set_ylabel("Number of students")
        ax.set_ylim(0, max(pass_fail.max() * 1.15, 1))
        fig.tight_layout()
        show_chart(fig)

    with chart_right2:
        st.subheader("Student percentage comparison")
        label_column = choose_label_column(view)
        chart_data = view.copy()
        if label_column is not None:
            chart_data["_label"] = chart_data[label_column].astype(str)
        else:
            chart_data["_label"] = ["Row " + str(i + 1) for i in range(len(chart_data))]
        chart_data = chart_data.sort_values(names["Percentage"], ascending=False)

        max_students_in_chart = 40
        if len(chart_data) > max_students_in_chart:
            half = max_students_in_chart // 2
            chart_data = pd.concat([chart_data.head(half), chart_data.tail(half)])
            st.caption(
                f"Showing the top {half} and bottom {half} of {len(view)} students so the chart stays readable. "
                "All matching students are in the results table below."
            )
        chart_data = chart_data.iloc[::-1]  # highest percentage at the top

        fig, ax = plt.subplots(figsize=(6, max(4, 0.25 * len(chart_data) + 1)))
        colors = ["#59A14F" if r == analysis.PASS_LABEL else "#E15759" for r in chart_data[names["Result"]]]
        ax.barh(chart_data["_label"], chart_data[names["Percentage"]], color=colors)
        ax.set_xlim(0, 100)
        ax.set_xlabel("Percentage (green = Pass, red = Fail)")
        ax.tick_params(axis="y", labelsize=8)
        fig.tight_layout()
        show_chart(fig)


st.header("Charts")
if filtered.empty:
    st.info("There are no matching students to chart. Change or clear the search/filters in the sidebar.")
else:
    if filters_active:
        st.caption(f"Charts show the {len(filtered)} student(s) that match your search/filters.")
    draw_charts(filtered)

# ---------------------------------------------------------------------------
# Results table, student details and download
# ---------------------------------------------------------------------------
st.header("Student results")
st.write(f"Showing **{len(filtered)}** of **{len(results)}** students.")

if filtered.empty:
    st.warning(
        analysis.describe_empty_result(
            results, search_text, search_columns, grade_filter, status_filter, names["Grade"], names["Result"]
        )
    )
    if searching and len(data_to_use) < len(df):
        in_file = analysis.filter_results(df, search_text, analysis.find_search_columns(df))
        if not in_file.empty:
            st.info(
                f"{len(in_file)} student(s) matching your search are in the uploaded file but were left out of "
                "the results because of invalid marks (see Data validation above)."
            )
else:
    if len(filtered) == 1:
        st.subheader("Student Details")
        st.dataframe(analysis.student_details_table(filtered.iloc[0]), hide_index=True, width="stretch")
    elif searching:
        st.write(f"**{len(filtered)} students match your search.** All of them are in the table below.")
        pick_labels = filtered[search_columns].astype(str).agg(" | ".join, axis=1).tolist()
        picked = st.selectbox(
            "Show full details for one of the matching students",
            options=list(range(len(filtered))),
            format_func=lambda i: pick_labels[i],
            key=f"pick-{data_key}",
        )
        st.subheader("Student Details")
        st.dataframe(analysis.student_details_table(filtered.iloc[picked]), hide_index=True, width="stretch")

    st.subheader("Matching records" if filters_active else "All records")
    st.dataframe(filtered, hide_index=True, width="stretch")

# Missing cells: say clearly which students the numbers describe.
st.subheader("Missing values: whole file vs current results")
original_columns = list(data_to_use.columns)
missing_whole_file = analysis.count_missing_cells(df)
missing_filtered = analysis.count_missing_cells(filtered, original_columns)
miss_left, miss_right = st.columns(2)
miss_left.metric(f"Missing cells in the complete uploaded dataset ({len(df)} rows)", missing_whole_file)
miss_right.metric(f"Missing cells in the current filtered results ({len(filtered)} rows)", missing_filtered)
if missing_filtered > 0:
    with st.expander("Missing cells per column (current filtered results)"):
        per_column = filtered[original_columns].isna().sum()
        st.dataframe(
            pd.DataFrame({"Column": per_column.index, "Missing cells": per_column.values})
            .query("`Missing cells` > 0"),
            hide_index=True,
            width="stretch",
        )

st.subheader("Download results")
download_cols = st.columns(2)
download_cols[0].download_button(
    "⬇️ Download all results (CSV)",
    data=analysis.results_to_csv(results),
    file_name="student_results.csv",
    mime="text/csv",
)
download_cols[1].download_button(
    "⬇️ Download filtered results (CSV)",
    data=analysis.results_to_csv(filtered),
    file_name="student_results_filtered.csv",
    mime="text/csv",
    disabled=filtered.empty,
)
