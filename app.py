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
            df["LessonID"] = range(1, len(df) +
