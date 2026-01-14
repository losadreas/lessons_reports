import streamlit as st
import pandas as pd
import hashlib
import io
from datetime import datetime

# -------------------------
# SESSION INIT
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

def load_excel(file):
    df = pd.read_excel(file)
    df["LessonDate"] = pd.to_datetime(df["LessonDate"])
    return df

def merge_data(existing, new):
    return pd.concat([existing, new], ignore_index=True)

# -------------------------
# UI
# -------------------------
st.title("Lesson Reports (Excel-based)")

tab1, tab2, tab3 = st.tabs([
    "📥 Import Excel",
    "📊 Student report",
    "📤 Export Excel"
])

# -------------------------
# TAB 1 — IMPORT
# -------------------------
with tab1:
    st.subheader("Import yearly Excel file")

    uploaded = st.file_uploader(
        "Upload Excel (.xlsx)",
        type=["xlsx"]
    )

    if uploaded:
        file_bytes = uploaded.getvalue()
        file_id = file_hash(file_bytes)

        if file_id in st.session_state.imported_files:
            st.error("This Excel file has already been imported in this session.")
        else:
            df_new = load_excel(io.BytesIO(file_bytes))

            required_cols = {"LessonID", "Student", "LessonDate"}
            if not required_cols.issubset(df_new.columns):
                st.error("Invalid Excel format.")
            else:
                st.session_state.data = merge_data(
                    st.session_state.data,
                    df_new
                )
                st.session_state.imported_files.add(file_id)
                st.success(f"Imported {len(df_new)} lessons")

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

# -------------------------
# TAB 3 — EXPORT
# -------------------------
with tab3:
    st.subheader("Export Excel")

    if st.session_state.data.empty:
        st.info("Nothing to export")
    else:
        export_df = st.session_state.data.copy()
        export_df = export_df.sort_values("LessonDate")

        output = io.BytesIO()
        export_df.to_excel(output, index=False)

        st.download_button(
            "Download yearly Excel",
            data=output.getvalue(),
            file_name=f"lessons_{datetime.now().year}.xlsx"
        )
