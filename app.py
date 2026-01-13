import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# -------------------------
# БАЗА ДАННЫХ
# -------------------------
conn = sqlite3.connect("lessons.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student TEXT NOT NULL,
    lesson_date DATE NOT NULL
)
""")
conn.commit()

# -------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# -------------------------
def add_lesson(student, lesson_date):
    cursor.execute(
        "INSERT INTO lessons (student, lesson_date) VALUES (?, ?)",
        (student, lesson_date)
    )
    conn.commit()

def load_lessons():
    return pd.read_sql("SELECT * FROM lessons", conn, parse_dates=["lesson_date"])

# -------------------------
# ИНТЕРФЕЙС
# -------------------------
st.title("Учёт уроков")

tab1, tab2, tab3, tab4 = st.tabs([
    "➕ Добавить урок",
    "📥 Импорт Excel",
    "📊 Отчёт по ученику",
    "📤 Экспорт Excel"
])

# -------------------------
# 1. ДОБАВЛЕНИЕ УРОКА
# -------------------------
with tab1:
    st.subheader("Добавить урок вручную")

    student = st.text_input("Имя ученика")
    lesson_date = st.date_input("Дата урока", value=date.today())

    if st.button("Добавить"):
        if student:
            add_lesson(student, lesson_date)
            st.success("Урок добавлен")
        else:
            st.error("Введите имя ученика")

# -------------------------
# 2. ИМПОРТ EXCEL
# -------------------------
with tab2:
    st.subheader("Импорт Excel")

    year = st.number_input("Год", min_value=2020, max_value=2100, value=date.today().year)
    month = st.number_input("Месяц", min_value=1, max_value=12, value=date.today().month)

    uploaded = st.file_uploader("Excel файл", type=["xlsx"])

    if uploaded and st.button("Импортировать"):
        df = pd.read_excel(uploaded)

        for _, row in df.iterrows():
            student = row[1]
            day = int(row[2])
            lesson_date = date(year, month, day)
            add_lesson(student, lesson_date)

        st.success("Импорт завершён")

# -------------------------
# 3. ОТЧЁТ ПО УЧЕНИКУ
# -------------------------
with tab3:
    st.subheader("Отчёт по ученику")

    df = load_lessons()

    if not df.empty:
        students = sorted(df["student"].unique())
        student = st.selectbox("Выберите ученика", students)

        student_df = df[df["student"] == student].copy()
        student_df["year_month"] = student_df["lesson_date"].dt.to_period("M")

        for period, group in student_df.groupby("year_month"):
            st.markdown(f"### {period}")
            group = group.sort_values("lesson_date")
            for i, d in enumerate(group["lesson_date"], start=1):
                st.write(f"{i}) {d.strftime('%d.%m.%Y')}")
            st.write(f"**Итого: {len(group)} занятий**")
    else:
        st.info("Пока нет данных")

# -------------------------
# 4. ЭКСПОРТ EXCEL
# -------------------------
with tab4:
    st.subheader("Экспорт Excel по месяцу")

    year = st.number_input("Год экспорта", min_value=2020, max_value=2100, value=date.today().year, key="exp_year")
    month = st.number_input("Месяц экспорта", min_value=1, max_value=12, value=date.today().month, key="exp_month")

    df = load_lessons()

    if st.button("Сформировать Excel"):
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
            "№ урока в месяце",
            "Имя ученика",
            "День месяца"
        ])

        st.download_button(
            "Скачать Excel",
            data=export_df.to_excel(index=False),
            file_name=f"lessons_{year}_{month}.xlsx"
        )
