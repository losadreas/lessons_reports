import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
import io

# =====================
# DATABASE (SESSION)
# =====================
conn = sqlite3.connect(":memory:", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student TEXT NOT NULL,
    lesson_date DATE NOT NULL
)
""")
conn.commit()

# =====================
# DB HELPERS
# =====================
def add_lesson(student, lesson_date):
    cursor.execute(
        "INSERT INTO lessons (student, lesson_date) VALUES (?, ?)",
        (student, lesson_date)
    )
    conn.commit()

def load_lessons():
    return pd.read_sql(
        "SELECT * FROM lessons",
        conn,
        parse_dates=["lesson_date"]
    )

def merge_students(old_name, new_name):
    cursor.execute(
        "UPDATE lessons SET student = ? WHERE student = ?",
        (new_name, old_name)
    )
    conn.commit()

# =====================
# UI
# =====================
st.title("Lesson Reports")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📥 Import Monthly",
    "📤 Export Monthly",
    "📥 Import Yearly",
    "📤 Export Yearly",
    "📊 Student Report"
])

# =====================
# TAB 1 — IMPORT MONTHLY
# =====================
with tab1:
    st.subheader("Import monthly Excel")

    year = st.number_input("Year", 2020, 2100, date.today().year)
    month = st.number_input("Month", 1, 12, date.today().month)

    uploaded = st.file_uploader("Excel file (.xlsx)", type=["xlsx"])

    if uploaded and st.button("Import"):
        df = pd.read_excel(uploaded)

        imported = 0
        for _, row in df.iterrows():
            try:
                student = str(row[1]).strip()
                day = int(float(row[2]))
                lesson_date = date(year, month, day)
                add_lesson(student, lesson_date)
                imported += 1
            except Exception:
                continue

        st.success(f"Imported {imported} lessons")

# =====================
# TAB 2 — EXPORT MONTHLY
# =====================
with tab2:
    st.subheader("Export monthly Excel")

    year = st.number_input("Export year", 2020, 2100, date.today().year, key="em_y")
    month = st.number_input("Export month", 1, 12, date.today().month, key="em_m")

    df = load_lessons()
    df = df[
        (df["lesson_date"].dt.year == year) &
        (df["lesson_date"].dt.month == month)
    ].sort_values(["student", "lesson_date"])

    if not df.empty:
        rows = []
        for student, group in df.groupby("student"):
            for i, d in enumerate(group["lesson_date"], start=1):
                rows.append([i, student, d.day])

        export_df = pd.DataFrame(
            rows,
            columns=["Lesson # in month", "Student", "Day of month"]
        )

        output = io.BytesIO()
        export_df.to_excel(output, index=False)

        st.download_button(
            "Download Excel",
            data=output.getvalue(),
            file_name=f"lessons_{year}_{month}.xlsx"
        )
    else:
        st.info("No lessons for this month")

# =====================
# TAB 3 — IMPORT YEARLY
# =====================
with tab3:
    st.subheader("Import yearly Excel")

    uploaded = st.file_uploader(
        "Yearly Excel (.xlsx)",
        type=["xlsx"],
        key="year_import"
    )

    if uploaded and st.button("Import yearly"):
        df = pd.read_excel(uploaded)

        df["LessonDate"] = pd.to_datetime(df["LessonDate"])

        for _, row in df.iterrows():
            add_lesson(row["Student"], row["LessonDate"])

        st.success(f"Imported {len(df)} lessons")

# =====================
# TAB 4 — EXPORT YEARLY
# =====================
with tab4:
    st.subheader("Export yearly Excel")

    year = st.number_input("Year", 2020, 2100, date.today().year, key="ey")

    df = load_lessons()
    df = df[df["lesson_date"].dt.year == year].sort_values("lesson_date")

    if not df.empty:
        export_df = df.rename(columns={
            "student": "Student",
            "lesson_date": "LessonDate"
        })[["Student", "LessonDate"]]

        output = io.BytesIO()
        export_df.to_excel(output, index=False)

        st.download_button(
            "Download yearly Excel",
            data=output.getvalue(),
            file_name=f"lessons_{year}.xlsx"
        )
    else:
        st.info("No data for selected year")

# =====================
# TAB 5 — STUDENT REPORT
# =====================
with tab5:
    st.subheader("Student report")

    df = load_lessons()

    if df.empty:
        st.info("No data")
    else:
        students = sorted(df["student"].unique())
        student = st.selectbox("Select student", students)

        student_df = df[df["student"] == student].copy()
        student_df["YearMonth"] = student_df["lesson_date"].dt.to_period("M")

        rows = []
        for period, group in student_df.groupby("YearMonth"):
            st.markdown(f"### {period}")
            for i, d in enumerate(group["lesson_date"], start=1):
                st.write(f"{i}) {d.strftime('%d.%m.%Y')}")
            st.write(f"**Total: {len(group)} lessons**")

            for d in group["lesson_date"]:
                rows.append([student, d])

        # EXPORT STUDENT REPORT
        export_df = pd.DataFrame(
            rows,
            columns=["Student", "LessonDate"]
        )

        output = io.BytesIO()
        export_df.to_excel(output, index=False)

        st.download_button(
            "Download student report",
            data=output.getvalue(),
            file_name=f"{student}_report.xlsx"
        )

        # ---------- MERGE STUDENTS ----------
        st.divider()
        st.subheader("Merge students (fix spelling)")

        other = st.selectbox(
            "Merge this name into current student",
            [s for s in students if s != student]
        )

        if st.button("Merge"):
            merge_students(other, student)
            st.success(f"Merged '{other}' into '{student}'")
