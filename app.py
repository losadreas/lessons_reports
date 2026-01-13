import streamlit as st
import pandas as pd
from datetime import date
import os
import io
import logging

# -------------------------
# CONFIG
# -------------------------
DATA_FILE = "lessons.csv"
LOG_FILE = "app.log"

# -------------------------
# LOGGING
# -------------------------
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logging.info("Application started")

# -------------------------
# DATA FUNCTIONS (CSV)
# -------------------------
def load_lessons():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df["lesson_date"] = pd.to_datetime(df["lesson_date"], errors="coerce")
        df = df.dropna(subset=["lesson_date"])
        return df
    else:
        return pd.DataFrame(columns=["student", "lesson_date"])


def save_lessons(df):
    df.to_csv(DATA_FILE, index=False)

def add_lesson(student, lesson_date):
    df = load_lessons()
    new_row = pd.DataFrame([{
        "student": student,
        "lesson_date": lesson_date
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    save_lessons(df)
    logging.info(f"Lesson added: {student}, {lesson_date}")

# -------------------------
# UI
# -------------------------
st.title("Lesson Reports")

tab1, tab2, tab3, tab4 = st.tabs([
    "➕ Add lesson",
    "📥 Import Excel",
    "📊 Student report",
    "📤 Export Excel"
])

# -------------------------
# TAB 1 — ADD LESSON
# -------------------------
with tab1:
    st.subheader("Add lesson manually")

    student = st.text_input("Student name")
    lesson_date = st.date_input("Lesson date", value=date.today())

    if st.button("Add lesson"):
        if student.strip():
            add_lesson(student.strip(), lesson_date)
            st.success("Lesson added")
        else:
            st.error("Student name is required")

# -------------------------
# TAB 2 — IMPORT EXCEL
# -------------------------
with tab2:
    st.subheader("Import from Excel")

    year = st.number_input("Year", min_value=2020, max_value=2100, value=date.today().year)
    month = st.number_input("Month", min_value=1, max_value=12, value=date.today().month)

    uploaded = st.file_uploader("Excel file (.xlsx)", type=["xlsx"])

    if uploaded and st.button("Import"):
        df_excel = pd.read_excel(uploaded)

        df = load_lessons()  # <-- ВАЖНО: загружаем ОДИН раз

        imported = 0
        errors = 0

        for _, row in df_excel.iterrows():
            student = str(row[1]).strip()

            if not student or student == "nan":
                continue

            try:
                day = int(float(row[2]))
                lesson_date = date(year, month, day)

                df = pd.concat([
                    df,
                    pd.DataFrame([{
                        "student": student,
                        "lesson_date": lesson_date
                    }])
                ], ignore_index=True)

                imported += 1

            except Exception:
                errors += 1
                logging.warning(f"Import error: {row}")

        save_lessons(df)  # <-- СОХРАНЯЕМ ОДИН РАЗ

        if errors > 0:
            st.warning(f"Imported: {imported}, skipped rows: {errors}")
        else:
            st.success(f"Imported {imported} lessons")


# -------------------------
# TAB 3 — STUDENT REPORT
# -------------------------
with tab3:
    st.subheader("Student report")

    df = load_lessons()

    if df.empty:
        st.info("No data available")
    else:
        students = sorted(df["student"].unique())
        student = st.selectbox("Select student", students)

        student_df = df[df["student"] == student].copy()
        student_df["year_month"] = student_df["lesson_date"].dt.to_period("M")

        for period, group in student_df.groupby("year_month"):
            st.markdown(f"### {period}")
            group = group.sort_values("lesson_date")

            for i, d in enumerate(group["lesson_date"], start=1):
                st.write(f"{i}) {d.strftime('%d.%m.%Y')}")

            st.write(f"**Total: {len(group)} lessons**")

# -------------------------
# TAB 4 — EXPORT EXCEL
# -------------------------
with tab4:
    st.subheader("Export to Excel")

    year = st.number_input(
        "Export year", min_value=2020, max_value=2100,
        value=date.today().year, key="exp_year"
    )
    month = st.number_input(
        "Export month", min_value=1, max_value=12,
        value=date.today().month, key="exp_month"
    )

    df = load_lessons()

    if st.button("Generate Excel"):
        mask = (
            (df["lesson_date"].dt.year == year) &
            (df["lesson_date"].dt.month == month)
        )
        month_df = df[mask].sort_values(["student", "lesson_date"])

        rows = []
        for student, group in month_df.groupby("student"):
            for i, d in enumerate(group["lesson_date"], start=1):
                rows.append([i, student, d.day])

        export_df = pd.DataFrame(rows, columns=[
            "Lesson # in month",
            "Student",
            "Day of month"
        ])

        output = io.BytesIO()
        export_df.to_excel(output, index=False)

        st.download_button(
            "Download Excel",
            data=output.getvalue(),
            file_name=f"lessons_{year}_{month}.xlsx"
        )

        logging.info(f"Excel exported: {year}-{month}")

