# Student Performance Analysis System

A simple, beginner-friendly Python mini-project. Upload a CSV file of student marks and the application
calculates each student's **total, average, percentage, grade and Pass/Fail result**, shows a class summary
and charts, lets you search and filter, and lets you download the results as a CSV file.

This is a **traditional data-analysis project**. It uses only Python, Pandas, Matplotlib and Streamlit.
It does **not** use AI, machine learning, external APIs, a database, or a login system.

---

## 1. Project overview

Teachers often keep marks in a spreadsheet and then work out totals, grades and pass/fail by hand.
This project automates that work. You upload the marks as a CSV file, choose which columns are subjects,
and the app does the calculations and shows the results in a web page that opens in your browser.

## 2. Objectives

- Read student marks from a CSV file and check that the data is valid.
- Calculate total marks, average marks, percentage, grade and Pass/Fail for every student.
- Show a simple class summary and four charts.
- Let the user search students and filter by grade or by Pass/Fail.
- Let the user download the calculated results.
- Keep the code simple, well organised and tested.

## 3. Features

| # | Feature | Where to find it |
|---|---|---|
| 1 | Home page with title, description and instructions | Top of the page |
| 2 | CSV upload | Sidebar |
| 3 | Dataset preview (rows, columns, column names, missing values) | "Dataset preview" section |
| 4 | Data validation with clear error messages; choose your own subject columns | "Data validation" section, sidebar |
| 5 | Total, average, percentage, grade, Pass/Fail for each student | "Student results" section |
| 6 | Performance summary (students, passed, failed, class average, highest, lowest) | "Performance summary" section |
| 7 | Four Matplotlib charts | "Charts" section |
| 8 | Search by ID/name; filter by grade and by Pass/Fail. Results, summary and charts follow the search/filters, and a matching student's full details are shown | Sidebar, "Student results" section |
| 9 | Download results as CSV | Bottom of the page |
| 10 | Sample dataset of 36 fictional students | `sample_students.csv`, or the sidebar checkbox |

## 4. Technology stack

| Tool | Version used | Purpose |
|---|---|---|
| Python | 3.12 (tested with 3.12.3) | Programming language |
| Pandas | 2.3.3 | Reading the CSV and doing the calculations |
| Matplotlib | 3.10.8 | Charts |
| Streamlit | 1.52.2 | The web interface |
| Pytest | 8.4.2 | Automated tests |

## 5. Project structure

```
student-performance-analysis/
│
├── app.py                 # Streamlit user interface (what you see)
├── analysis.py            # Calculation and validation logic (no Streamlit code)
├── requirements.txt       # List of packages to install
├── sample_students.csv    # 36 FICTIONAL students for demonstration
├── README.md              # This file
├── .gitignore             # Files that Git should ignore
│
└── tests/
    └── test_analysis.py   # Automated tests for analysis.py
```

`app.py` only handles display. All calculations and checks are in `analysis.py`, so they can be tested without opening the web page.

## 6. Dataset format

Your CSV file needs:

- A **header row** (the first line holds the column names).
- **One row per student.**
- **One column per subject**, containing numeric marks.
- Comma-separated values, saved as **UTF-8** (in Excel: *Save As → CSV UTF-8*).

Example:

```csv
Student_ID,Name,Gender,Mathematics,English,Science,Computer
S001,Aarav Sharma,Male,96,92,95,98
S002,Ananya Iyer,Female,94,97,91,96
```

- `Student_ID`, `Name` and `Gender` are **optional** and the column names are **not fixed**. If the app finds a column
  whose name contains "name" or "roll", or looks like an ID column (`ID`, `Student_ID`, `Student ID`, `StudentID`),
  it uses it for searching. If there is no such column, searching is simply turned off.
- Other columns (Age, Attendance, Quiz scores ...) are kept and shown in the results. The app only *suggests* columns
  that look like marks as subjects; it skips names such as age, attendance, total, percentage, grade and result.
  You can change the selection at any time.
- Subject columns can have **any names** and any number of subjects. You choose them in the sidebar
  (the app suggests the columns that look like marks).
- **Marks are assumed to be between 0 and 100.** You can change the maximum (and the passing marks) under
  *Advanced settings* in the sidebar.
- The included `sample_students.csv` has an extra column, `Data_Type`, which says "Fictional demo data".
  Extra columns are kept in the results and the download.

> **The sample dataset is fictional.** All names and marks in `sample_students.csv` were made up for demonstration.
> They do not describe any real person.

## 7. Grade calculation rules

```
Percentage = Total marks ÷ (Number of subjects × Maximum marks) × 100
```

(With the default maximum of 100 per subject, the percentage equals the average mark.)
The percentage is rounded to 2 decimal places, and the grade is taken from that rounded percentage.

| Percentage | Grade |
|---|---|
| 90 – 100 | A+ |
| 80 – 89.99 | A |
| 70 – 79.99 | B |
| 60 – 69.99 | C |
| 50 – 59.99 | D |
| Below 50 | F |

## 8. Pass/Fail rules

- The passing mark is **40 in every selected subject** (changeable in *Advanced settings*).
- If a student scores **below 40 in any one subject**, the student is **Fail**.
- Otherwise the student is **Pass**.

**Important:** grade and Pass/Fail are decided **separately**, exactly as the rules above say. So:

- A student with 45 in every subject has percentage 45 → grade **F**, but **Pass** (nothing is below 40).
- A student with 92, 38, 90, 95 has percentage 78.75 → grade **B**, but **Fail** (38 is below 40).

**Missing or invalid marks are never treated as zero.** If a mark is missing, not a number, below 0, or above the
maximum, the app tells you exactly where the problem is and does not calculate results until you fix the file
or choose to leave those rows out.

## Search and filter rules

All active conditions must be true **at the same time** (logical AND). Start with all students, then:

1. **Search** (optional) - type in the sidebar box and press **Enter**:
   - **Names:** partial match, ignoring capital letters and extra spaces. `jamie` finds `Jamie Jones` and `Jamie Smith`;
     `  JAMIE   jones ` finds `Jamie Jones`.
   - **Student IDs:** the **whole ID** must match. `14` finds student 14 only, not 114 or 140. Numeric IDs and text IDs
     (`S010`) both work, and `14` also matches `14.0`.
   - An empty search keeps every student that satisfies the other filters.
2. **Filter by grade** - one or more grades (A+, A, B, C, D, F). Uses the grade calculated by the app.
3. **Filter by Pass / Fail** - uses the passing marks of the calculation (default 40 in every subject).

Clearing one control removes only that restriction. If nobody matches, the app says why
(for example *No students found matching your search.*) and never falls back to showing everyone.

What follows the search/filters: the **results table**, the **Student Details** section, the **performance summary**,
the **four charts** and the **filtered CSV download**. The **Download all results** button always contains everyone.

**Student Details:** when exactly one student matches, a *Student Details* section lists **every column of the uploaded file**
(ID, name, age, gender, quizzes, assignments, midterm, final, attendance ... whatever your file has) followed by the
calculated total, average, percentage, grade and result. Empty cells are shown as `(missing)`; nothing is invented.
When several students match, they all appear in the table, and a drop-down lets you open any one of them in full.

**If your file already has columns named like the calculated ones** (`Percentage`, `Grade`, `Result`, ...), your columns are
kept unchanged and the app's columns are named `Calculated_...`. The grade/Pass-Fail filters, summary and charts use the
calculated columns, and the app shows a note explaining this.

**Missing values** are reported in two places: the *Dataset preview* counts the **complete uploaded file**, and the
*Missing values* block under the results compares the complete file with the **currently filtered results**.

## 9. Installation instructions

You need **Python 3.12** installed. Check with `py -3.12 --version` in PowerShell.

Open **Windows PowerShell** and run the commands below one by one.

> **Replace the example path** `C:\path\to\student-performance-analysis` in the first command with the real folder
> where you unzipped the project (for example `C:\Users\YourName\Documents\student-performance-analysis`).

```powershell
cd "C:\path\to\student-performance-analysis"

py -3.12 -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip setuptools wheel

python -m pip install -r requirements.txt
```

What these do: go to the project folder, create a private Python environment named `.venv`, switch it on,
update the install tools, and install the packages from `requirements.txt`.

**If PowerShell says "running scripts is disabled"** when you activate the environment, run this once and try again
(it only affects the current window):

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

When the environment is active you will see `(.venv)` at the start of the prompt.

*macOS / Linux users:* use `python3.12 -m venv .venv` and `source .venv/bin/activate` instead, then the same `pip` commands.

## 10. How to run the application

With the environment active (you see `(.venv)`):

```powershell
python -m streamlit run app.py
```

Your browser opens at `http://localhost:8501`. If it does not, copy that address into your browser.
To stop the app, press `Ctrl + C` in PowerShell.

## 11. How to run the tests

```powershell
python -m pytest -q
```

All tests should pass. They check totals, averages, percentages, grades, Pass/Fail, every kind of invalid data
(missing columns, text marks, negative marks, marks above 100, empty files, missing marks), filtering, CSV export,
and the sample dataset.

## 12. How to upload data

1. Start the app (section 10).
2. In the **sidebar**, click **Browse files** under *Upload a CSV file* and choose your `.csv` file.
   (Or tick **Use the sample dataset (fictional)** to try the app first.)
3. Look at the **Dataset preview** to check the file was read correctly.
4. Under **Choose subject columns** in the sidebar, make sure only the columns that hold marks are selected.
   Remove any column that is not a subject (for example "Age").
5. Read the **Data validation** section. A green message means everything is fine.
   Red messages explain the problems and list the affected rows with their line numbers in your file.
   Fix the CSV and upload it again, or tick *Leave these rows out of the calculation and continue*
   (the app then tells you how many rows were left out).

## 13. How to download results

Scroll to the bottom of the page, to **Download results**:

- **Download all results (CSV)** saves `student_results.csv` with every student.
- **Download filtered results (CSV)** saves only the students currently shown after your search/filters.

The file contains **all your original columns** followed by five calculated columns:
`Total_Marks`, `Average_Marks`, `Percentage`, `Grade`, `Result`.
(If your file already has a column with one of those names, the new column is named `Calculated_...`
and your original column is left untouched.)

## 14. Limitations

- Only **CSV** files are supported (not `.xlsx`). Save Excel files as *CSV UTF-8* first. Files that use semicolons
  or tabs instead of commas, or a non-UTF-8 encoding, are rejected with a helpful message.
- The grade scale is fixed in the code (`GRADE_SCALE` in `analysis.py`). Only the maximum marks and the passing marks can be changed in the app.
- All subjects count equally (no weighting), and the maximum and passing marks are the same for every subject.
- The app expects **one row per student** and does not check for duplicate students.
- Rows with missing or invalid marks are **not** repaired automatically. You must fix the file or choose to leave those rows out.
- The search box applies when you press **Enter** or click elsewhere. Streamlit text boxes do not update on every key press.
- ID search needs the whole ID (`S01` does not find `S010`). Names use partial matching.
- The "Student percentage comparison" chart shows at most 40 students (the top 20 and bottom 20) so that it stays readable.
  The results table and download always include everyone.
- The column suggestion is a guess: any numeric column (such as "Age") may be suggested as a subject, so check the selection in the sidebar.
- Everything is processed in memory; the app is meant for small class-sized files, not huge datasets.
- Created and tested on Linux with Python 3.12.3. The Windows PowerShell commands above use standard Python tools but were not run on a Windows machine.
