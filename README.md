<div align="center">

# 🎓 Student Performance Analysis System

### Analyze Student Results. Discover Performance. Make Better Decisions.

A Python-based interactive dashboard for analyzing student marks, calculating results, and visualizing academic performance.

<br>

<a href="https://student-performance-analysis-ggztvejeupesjzqbma7eeg.streamlit.app/">
  <img src="https://img.shields.io/badge/🚀_LIVE_DEMO-Open_Application-FF4B4B?style=for-the-badge" alt="Live Demo">
</a>

<a href="https://github.com/AshishMandalDSAI/Student-Performance-Analysis">
  <img src="https://img.shields.io/badge/GitHub-View_Repository-181717?style=for-the-badge&logo=github" alt="GitHub Repository">
</a>

<br><br>

![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square\&logo=python\&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=flat-square\&logo=streamlit\&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-Data_Analysis-150458?style=flat-square\&logo=pandas\&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-Visualization-11557C?style=flat-square)

</div>

---

## 🌐 Live Application

**Try the application here:**

### 👉 [Launch Student Performance Analysis System](https://student-performance-analysis-ggztvejeupesjzqbma7eeg.streamlit.app/)

Explore the dashboard, analyze student performance, and use the available features directly in your browser.

## 📌 About the Project

The **Student Performance Analysis System** is an interactive data analysis application developed using Python and Streamlit.

It helps users understand student academic performance by organizing marks, calculating performance metrics, displaying results, and presenting data through visualizations.

The project demonstrates how Python libraries can transform student records into useful information through an easy-to-use web dashboard.

**Project Category:** Data Analytics | Python | Data Visualization

## ✨ Key Features

* 📂 **Student Data Analysis** — Analyze student records from supported datasets.
* 🧮 **Automatic Calculations** — Calculate total marks, averages, and percentages using the application's configured logic.
* 🏆 **Grade Analysis** — Display student grades based on the implemented grading rules.
* ✅ **Pass/Fail Identification** — Identify student results using the application's configured criteria.
* 🔍 **Student Search** — Find student records using supported search fields.
* 🎯 **Interactive Filters** — Filter records using the available filtering options.
* 📊 **Data Visualization** — Explore performance through charts and graphical summaries.
* 👨‍🎓 **Student Details** — Review matching student information where supported.
* 📥 **Result Export** — Download results in CSV format if the export feature is available.
* 🧪 **Automated Testing** — Test the analysis logic with the project's test suite.

*The available functionality depends on the current application implementation.*

## 🛠️ Technology Stack

| Technology | Purpose                        |
| ---------- | ------------------------------ |
| Python     | Core application development   |
| Pandas     | Data manipulation and analysis |
| Matplotlib | Data visualization             |
| Streamlit  | Interactive web application    |
| Pytest     | Automated testing              |

## 📸 Application Overview

The application is designed to make student performance data easier to explore and understand.

Users can open the live dashboard, inspect the available metrics and charts, and use the supported search, filter, and export features.

**Live Preview:** [Open the Application](https://student-performance-analysis-ggztvejeupesjzqbma7eeg.streamlit.app/)

## 📁 Project Structure

```text
Student-Performance-Analysis/
│
├── app.py
├── analysis.py
├── requirements.txt
├── sample_students.csv
├── README.md
│
└── tests/
    └── test_analysis.py
```

| File                     | Description                                   |
| ------------------------ | --------------------------------------------- |
| `app.py`                 | Streamlit dashboard and application interface |
| `analysis.py`            | Data analysis and calculation logic           |
| `requirements.txt`       | Required Python packages                      |
| `sample_students.csv`    | Sample student dataset                        |
| `tests/test_analysis.py` | Automated tests                               |
| `README.md`              | Project documentation                         |

## 🧮 Student Performance Calculations

A common percentage calculation is:

```text
Percentage = (Marks Obtained / Maximum Possible Marks) × 100
```

For multiple subjects:

```text
Total Marks = Subject 1 + Subject 2 + ... + Subject N
```

The maximum possible marks depend on the number of subjects and the scoring system.

Grades and Pass/Fail results are determined by the rules implemented in the application.

## 💡 Example Use Case

Imagine a teacher has a dataset containing student IDs, names, and marks in multiple subjects.

Using this application, the teacher can:

1. Explore student records.
2. Review academic performance.
3. Compare available performance metrics.
4. Search for individual students.
5. Apply available filters.
6. Download results if the export feature is enabled.

This can help make routine academic data analysis more convenient.

## 💻 Run the Project Locally

### Prerequisites

* Python installed on your computer.
* Git installed if you want to clone the repository.
* A terminal such as Windows PowerShell.

### Step 1: Clone the Repository

```bash
git clone https://github.com/AshishMandalDSAI/Student-Performance-Analysis.git
```

### Step 2: Open the Project Directory

```bash
cd Student-Performance-Analysis
```

### Step 3: Create a Virtual Environment

```bash
python -m venv .venv
```

### Step 4: Activate the Environment

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 5: Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### Step 6: Run the Application

```bash
python -m streamlit run app.py
```

Open the local address displayed in your terminal. Streamlit commonly uses:

```text
http://localhost:8501
```

## 🧪 Run Automated Tests

Run the test suite with:

```bash
python -m pytest -q
```

The terminal will display the actual test results.

## 🚀 Deployment

The project has a public Streamlit application link:

**Live App:**
https://student-performance-analysis-ggztvejeupesjzqbma7eeg.streamlit.app/

**GitHub Source Code:**
https://github.com/AshishMandalDSAI/Student-Performance-Analysis

The application source code is maintained in GitHub, while the live dashboard is accessible through Streamlit Community Cloud.

Official deployment guide: [Streamlit Community Cloud Documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)

## 🔮 Future Improvements

Potential improvements for future versions include:

* 📊 More interactive charts and performance comparisons.
* 📄 Downloadable PDF reports.
* 📈 Subject-wise and student-wise analysis.
* 📂 Additional supported file formats.
* 🛡️ Improved data validation and error handling.
* 🎨 Further improvements to dashboard design and usability.
* 📱 Better mobile responsiveness.

## 👨‍💻 Author

**Ashish Mandal**

* **GitHub Profile:** [AshishMandalDSAI](https://github.com/AshishMandalDSAI)
* **Project Repository:** [Student Performance Analysis System](https://github.com/AshishMandalDSAI/Student-Performance-Analysis)
* **Live Demo:** [Open the Application](https://student-performance-analysis-ggztvejeupesjzqbma7eeg.streamlit.app/)

## 📄 License

No license is specified in this README. Add a `LICENSE` file if you want to define the terms under which others may use, modify, or distribute the project.

---

<div align="center">

### ⭐ Explore the project and try the live demo!

**Built with Python, Pandas, Matplotlib, and Streamlit.**

</div>
