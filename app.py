import streamlit as st
import pandas as pd
import hashlib
import io
from datetime import date, datetime

# -------------------------
# SESSION STATE
# -------------------------
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(
        columns=["LessonID", "Student", "LessonDate"]
    )

if "imported_files" not in st.session_state:
    st.session_state.imported_files = set()

# -------------------------
# HELPERS
# -------------------------
def file_hash(file_bytes):
    return hashlib.md5(file_bytes).hexdigest()

def normalize_columns(df):
    df.columns = [c.strip().lower() for c in df.columns]
    return df

def load_excel(file, year=None, month=None):
    df = pd.read_excel(file)
    df = normalize_columns(df)

    cols = set(df.columns)

    # ---------- YEARLY FORMAT ----------
    if {"student", "lessondate"}.issubset(cols):
        df = df.rename(columns={
            "student": "Student",
            "lessondate": "LessonDate",
            "lessonid": "LessonID"
        })

        if "LessonID" not in df.columns:
            df["LessonID"] = range(1, len(df) + 1)

        df["LessonDate"] = pd.to_datetime(df["LessonDate"])

        return df[["LessonID", "Student", "LessonDate"]]

    # ---------- MONTHLY FORMAT ----------
    if {"имя ученика", "день месяца"}.issubset(cols) or {"student", "day of month"}.issubset(cols):
        if not year or not month:
            raise ValueError("Year and month are required for monthly import")

        # определяем колонки
        student_col = "имя ученика" if "имя ученика" in cols else "student"
        day_col = "день месяца" if "день месяца" in cols else "day of month"

        rows = []
        for i, row in df.iterrows():
            try:
                student = str(row[student_col]).strip()
                day = int(float(row[day_col]))
                lesson_date = date(year, month, day)

                rows.append({
                    "LessonID": i + 1,
                    "Student": student,
                    "LessonDate": lesson_date
                })
            except Exception:
                continue

        return pd.DataFrame(rows)

    raise ValueError("Unrecognized Excel format")

def merge_data(existing, new):
    combined = pd.concat([existing, new], ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["Student", "LessonDate"]
    )
    return combined

# -------------------------
# UI
# -------------------------
st.title("Lesson Reports")

tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Import Excel",
    "📊 Student report",
    "📆 Monthly export",
    "📅 Yearly export"
])

# -------------------------
# TAB 1 — IMPORT
# -------------------------
with tab1:
    st.subheader("Import Excel (monthly or yearly)")

    import_type = st.radio(
        "Excel type",
        ["Monthly report", "Yearly report"]
    )

    year = month = None
    if import_type == "Monthly report":
        year = st.number_input("Year", 2020, 2100, date.today().year)
        month = st.number_input("Month", 1, 12, date.today().month)

    uploaded = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])

    if uploaded:
        file_bytes = uploaded.getvalue()
        file_id = file_hash(file_bytes)

        if file_id in st.session_state.imported_files:
            st.error("This Excel file was already imported.")
        else:
            try:
                df_new = load_excel(
                    io.BytesIO(file_bytes),
                    year=year,
                    month=month
                )
                st.session_state.data = merge_data(
                    st.session_state.data,
                    df_new
                )
                st.session_state.imported_files.add(file_id)
                st.success(f"Imported {len(df_new)} lessons")
            except Exception as e:
                st.error(str(e))

# -------------------------
# TAB 2 — REPORT
# -------------------------
with tab2:
    st.subheader("Student report")

    df = st.session_state.data

    if df.empty:
        st.info("No data loaded")
    else:
        students = sorted(df["Student"].unique())
        student = st.selectbox("Select student", students)

        student_df = df[df["Student"] == student].copy()
        student_df["YearMonth"] = student_df["LessonDate"].dt.to_period("M")

        for period, group in student_df.groupby("YearMonth"):
            st.markdown(f"### {period}")
            group = group.sort_values("LessonDate")

            for i, d in enumerate(group["LessonDate"], start=1):
                st.write(f"{i}) {d.strftime('%d.%m.%Y')}")

            st.write(f"**Total: {len(group)} lessons**")

        st.markdown(
            f"### Year total: **{len(student_df)} lessons**"
        )

# -------------------------
# TAB 3 — MONTHLY EXPORT
# -------------------------
with tab3:
    st.subheader("Monthly Excel export")

    year = st.number_input("Export year", 2020, 2100, date.today().year, key="exp_y")
    month = st.number_input("Export month", 1, 12, date.today().month, key="exp_m")

    df = st.session_state.data
    mask = (
        (df["LessonDate"].dt.year == year) &
        (df["LessonDate"].dt.month == month)
    )
    month_df = df[mask].sort_values(["Student", "LessonDate"])

    if not month_df.empty:
        rows = []
        for student, group in month_df.groupby("Student"):
            for i, d in enumerate(group["LessonDate"], start=1):
                rows.append([i, student, d.day])

        export_df = pd.DataFrame(
            rows,
            columns=["Lesson # in month", "Student", "Day of month"]
        )

        output = io.BytesIO()
        export_df.to_excel(output, index=False)

        st.download_button(
            "Download monthly Excel",
            data=output.getvalue(),
            file_name=f"lessons_{year}_{month}.xlsx"
        )
    else:
        st.info("No lessons for this month")

# -------------------------
# TAB 4 — YEARLY EXPORT
# -------------------------
with tab4:
    st.subheader("Yearly Excel export")

    year = st.number_input("Year", 2020, 2100, date.today().year, key="yearly")

    year_df = st.session_state.data[
        st.session_state.data["LessonDate"].dt.year == year
    ].sort_values("LessonDate")

    if not year_df.empty:
        output = io.BytesIO()
        year_df.to_excel(output, index=False)

        st.download_button(
            "Download yearly Excel",
            data=output.getvalue(),
            file_name=f"lessons_{year}.xlsx"
        )
    else:
        st.info("No data for selected year")
