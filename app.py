import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import io

st.set_page_config(page_title="Lesson Reports", layout="centered")

# =====================
# DATABASE (SESSION SAFE)
# =====================
if "conn" not in st.session_state:
    st.session_state.conn = sqlite3.connect(":memory:", check_same_thread=False)
    st.session_state.cursor = st.session_state.conn.cursor()

    st.session_state.cursor.execute("""
    CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student TEXT NOT NULL,
        lesson_date DATE NOT NULL
    )
    """)
    st.session_state.conn.commit()

conn = st.session_state.conn
cursor = st.session_state.cursor

# =====================
# DB HELPERS
# =====================
def add_lesson(student, lesson_date):
    cursor.execute(
        "INSERT INTO lessons (student, lesson_date) VALUES (?, ?)",
        (student.strip(), lesson_date)
    )
    conn.commit()

def load_lessons():
    return pd.read_sql(
        "SELECT * FROM lessons",
        conn,
        parse_dates=["lesson_date"]
    )

def merge_students(source, target):
    cursor.execute(
        "UPDATE lessons SET student = ? WHERE student = ?",
        (target, source)
    )
    conn.commit()

# =====================
# UI
# =====================
st.title("Lesson Reports")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📥 Import Monthly",
    "📤 Export Monthly",
    "📥 Import Yearly",
    "📤 Export Yearly",
    "📊 Student Report",
    "🔗 Merge Students"
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

    year = st.number_input("Year", 2020, 2100, date.today().year, key="em_y")
    month = st.number_input("Month", 1, 12, date.today().month, key="em_m")

    df = load_lessons()
    df = df[
        (df["lesson_date"].dt.year == year) &
        (df["lesson_date"].dt.month == month)
    ].sort_values(["student", "lesson_date"])

    if df.empty:
        st.info("No lessons for selected month")
    else:
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

# =====================
# TAB 3 — IMPORT YEARLY
# =====================
with tab3:
    st.subheader("Import yearly Excel")

    uploaded = st.file_uploader("Yearly Excel (.xlsx)", type=["xlsx"], key="year_imp")

    if uploaded and st.button("Import yearly"):
        df = pd.read_excel(uploaded)
        df["LessonDate"] = pd.to_datetime(df["LessonDate"])

        for _, row in df.iterrows():
            add_lesson(row["Student"], row["LessonDate"].date())

        st.success(f"Imported {len(df)} lessons")

# =====================
# TAB 4 — EXPORT YEARLY
# =====================
with tab4:
    st.subheader("Export yearly Excel")

    year = st.number_input("Year", 2020, 2100, date.today().year, key="ey")

    df = load_lessons()
    df = df[df["lesson_date"].dt.year == year].sort_values("lesson_date")

    if df.empty:
        st.info("No data for selected year")
    else:
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
                st.write(f"{i}. {d.strftime('%d.%m.%Y')}")
            st.write(f"**Total: {len(group)} lessons**")

            for d in group["lesson_date"]:
                rows.append([student, d])

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

# =====================
# TAB 6 — MERGE STUDENTS
# =====================
with tab6:
    st.subheader("Merge students (manual)")

    df = load_lessons()

    if df.empty:
        st.info("No data")
    else:
        students = sorted(df["student"].unique())

        col1, col2 = st.columns(2)

        with col1:
            source = st.selectbox("Merge FROM (wrong spelling)", students)

        with col2:
            target = st.selectbox(
                "Merge INTO (correct name)",
                [s for s in students if s != source]
            )

        if st.button("Merge students"):
            merge_students(source, target)
            st.success(f"Merged '{source}' into '{target}'")
