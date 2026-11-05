from datetime import datetime
import io
from google import genai
import pandas as pd
import sqlite3
import streamlit as st

# --- DATABASE SETUP ---
conn = sqlite3.connect("dental_clinic.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age TEXT,
        phone TEXT,
        visit_date TEXT,
        treatment_notes TEXT
    )
"""
)
conn.commit()


def export_to_excel():
    df = pd.read_sql(
        "SELECT id, name, age, phone, visit_date, treatment_notes FROM patients",
        conn,
    )
    df.to_excel("dental_patients.xlsx", index=False)


# --- APP UI CONFIGURATION ---
st.set_page_config(
    page_title="ClinicFlow Gemini Pro - Dental Practice Manager",
    layout="wide",
)

st.title("🦷 ClinicFlow Gemini Pro: Autonomous Practice Manager")
st.write(
    "Powered by the official Google Gemini API for true conversational reasoning over patient databases."
)

# --- SIDEBAR CONFIGURATION & API KEY INPUT ---
menu = st.sidebar.selectbox(
    "Navigation Hub",
    [
        "Dashboard & Analytics",
        "Add Patient Visit",
        "Patient Search & Records",
        "🤖 Gemini AI Assistant",
    ],
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔑 Gemini API Settings")
user_api_key = st.sidebar.text_input(
    "Enter your Gemini API Key:", type="password", placeholder="AIzaSy..."
)

st.sidebar.markdown("---")
st.sidebar.subheader("📁 Data & Backups")

if st.sidebar.button("Download Excel Backup"):
    export_to_excel()
    with open("dental_patients.xlsx", "rb") as f:
        st.sidebar.download_button(
            label="📥 Click to Download .xlsx",
            data=f,
            file_name=f"dental_backup_{datetime.today().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# --- TAB 1: DASHBOARD & QUICK STATS ---
if menu == "Dashboard & Analytics":
    st.header("📊 Practice Analytics Dashboard")

    cursor.execute("SELECT COUNT(DISTINCT name) FROM patients")
    total_patients = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM patients")
    total_visits = cursor.fetchone()[0]

    today_str = datetime.today().strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT COUNT(*) FROM patients WHERE visit_date = ?", (today_str,)
    )
    visits_today = cursor.fetchone()[0]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Unique Patients", total_patients)
    col2.metric("Total Recorded Visits", total_visits)
    col3.metric("Visits Today", visits_today)

    st.markdown("---")
    st.subheader("📋 Recent Clinic Activity")
    cursor.execute(
        "SELECT name, age, phone, visit_date, treatment_notes FROM patients ORDER BY id DESC LIMIT 5"
    )
    recent = cursor.fetchall()
    if recent:
        for r in recent:
            st.info(
                f"**{r[0]}** (Age: {r[1]}) visited on **{r[3]}** — *Notes:* {r[4]}"
            )
    else:
        st.write("No visits recorded yet.")

# --- TAB 2: ADD PATIENT VISIT ---
elif menu == "Add Patient Visit":
    st.header("Record a New Patient Visit")

    with st.form("visit_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Patient Full Name")
            age = st.text_input("Age")
        with col2:
            phone = st.text_input("Phone Number")
            visit_date = st.date_input(
                "Date of Visit", value=datetime.today()
            ).strftime("%Y-%m-%d")

        treatment_notes = st.text_area(
            "Treatment & Medical Notes (e.g., Cleaning, Root canal on tooth #14)"
        )

        submitted = st.form_submit_button("Save Visit Record")

        if submitted:
            if name.strip() == "":
                st.error("Patient name cannot be empty.")
            else:
                cursor.execute(
                    """
                    INSERT INTO patients (name, age, phone, visit_date, treatment_notes)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (name, age, phone, visit_date, treatment_notes),
                )
                conn.commit()
                export_to_excel()
                st.success(
                    f"Successfully saved record for **{name}**! Updated database and Excel spreadsheet."
                )

# --- TAB 3: SEARCH & RECORDS ---
elif menu == "Patient Search & Records":
    st.header("Patient Database & Multi-Visit Timeline")

    search_query = st.text_input(
        "🔍 Search records by name, phone, or treatment keyword:"
    )

    if search_query:
        query_string = f"%{search_query}%"
        cursor.execute(
            """
            SELECT id, name, age, phone, visit_date, treatment_notes 
            FROM patients 
            WHERE name LIKE ? OR treatment_notes LIKE ? OR phone LIKE ?
            ORDER BY visit_date DESC
        """,
            (query_string, query_string, query_string),
        )
        results = cursor.fetchall()
    else:
        cursor.execute(
            """
            SELECT id, name, age, phone, visit_date, treatment_notes 
            FROM patients 
            ORDER BY visit_date DESC
        """
        )
        results = cursor.fetchall()

    st.subheader(f"Matching Records ({len(results)} found):")

    if results:
        patients_dict = {}
        for row in results:
            p_name = row[1]
            if p_name not in patients_dict:
                patients_dict[p_name] = {
                    "age": row[2],
                    "phone": row[3],
                    "visits": [],
                }
            patients_dict[p_name]["visits"].append(
                {"date": row[4], "notes": row[5]}
            )

        for p_name, data in patients_dict.items():
            with st.expander(
                f"📁 {p_name} (Age: {data['age']} | Phone: {data['phone']}) — {len(data['visits'])} Visit(s)"
            ):
                st.write(
                    f"**Contact Number:** {data['phone'] if data['phone'] else 'Not provided'}"
                )
                st.markdown("### 🕒 Visit History Timeline:")
                for v in data["visits"]:
                    st.markdown(
                        f"- **Date:** `{v['date']}` | **Notes:** {v['notes']}"
                    )
    else:
        st.info("No matching patient records found.")

# --- TAB 4: GEMINI AI ASSISTANT ---
elif menu == "🤖 Gemini AI Assistant":
    st.header("🤖 Gemini Clinic Intelligence")
    st.write(
        "Ask complex questions, request summaries, or filter patients naturally using Google Gemini's reasoning engine."
    )

    if not user_api_key:
        st.warning(
            "⚠️ Please enter your Gemini API Key in the left sidebar to activate the AI assistant."
        )
    else:
        try:
            client = genai.Client(api_key=user_api_key)
        except Exception as e:
            client = None

        user_prompt = st.text_input(
            "Ask Gemini anything about your clinic records:",
            placeholder="e.g., Which patients are under 50 and had a root canal?",
        )

        if user_prompt:
            df = pd.read_sql(
                "SELECT name, age, phone, visit_date, treatment_notes FROM patients",
                conn,
            )

            if df.empty:
                st.warning("Your database has no patient records yet.")
            else:
                database_text = df.to_string(index=False)

                prompt = f"""
                You are an expert AI clinical data assistant embedded inside a dental practice management app.
                Here is the current patient database exported from SQLite:
                {database_text}

                Answer the user's question accurately, professionally, and insightfully based ONLY on the database table above. 
                If the user asks to find people matching certain conditions (like age ranges or treatments), perform the logical reasoning to filter them correctly.

                User Question: {user_prompt}
                """

                with st.spinner("Gemini is analyzing records..."):
                    try:
                        response = client.models.generate_content(
                            model="gemini-3.8-flash",
                            contents=prompt,
                        )
                        st.markdown("### 💡 Gemini's Analysis:")
                        st.write(response.text)
                    except Exception as ex:
                        st.error(
                            f"An error occurred while calling the Gemini API: {ex}"
                        )