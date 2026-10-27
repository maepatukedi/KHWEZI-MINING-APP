import streamlit as st
import pandas as pd
import altair as alt
import base64
import importlib
import sqlite3
import json

from pathlib import Path
from contextlib import contextmanager

# KHWEZI MINING - COMPLETE APPLICATION

BASE = Path(__file__).resolve().parent
DATABASE = BASE / "safety_incidents.db"
USERS_FILE = BASE / "users.json"

ALL_ROLES = {
    "Administrator", "Safety Officer", "Mining Engineer",
    "Maintenance Engineer", "Manager"
}

SAFETY_ROLES = {
    "Administrator",
    "Safety Officer",
    "Mining Engineer",
    "Manager"
}

EQUIPMENT_ROLES = {
    "Administrator",
    "Mining Engineer",
    "Maintenance Engineer",
    "Manager"
}

FIELDS = [
    "incident_date",
    "incident_time",
    "shift",
    "location",
    "department",
    "incident_type",
    "category",
    "severity",
    "injury_status",
    "lost_time_status",
    "cause",
    "corrective_action",
    "incident_status",
    "likelihood",
    "consequence",
    "risk_score",
    "risk_classification"
]
# STREAMLIT PAGE CONFIGURATION

st.set_page_config(
    page_title="KHWEZI MINING | Health, Safety & Equipment",
    page_icon=" ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# COAL MINING COLOURS AND DESIGN


st.markdown("""
<style>

[data-testid="stAppViewContainer"] {
    background: linear-gradient(
        110deg,
        #f7f3eb,
        #fffdfa 50%,
        #edf1ee
    );
}

[data-testid="stSidebar"] {
    background: linear-gradient(
        165deg,
        #111820,
        #29343c 65%,
        #151c23
    );

    border-right: 4px solid #d9a435;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #f1c86e !important;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label {
    color: #f6f0e2 !important;
}

[data-testid="stSidebar"]
[data-baseweb="select"] * {
    color: #26313a !important;
}

[data-testid="stMetric"] {
    background: white;
    border-left: 6px solid #d9a435;
    border-radius: 14px;
    padding: 18px;

    box-shadow:
        0 6px 16px rgba(25,34,39,.09);
}

.mine-hero {
    border-radius: 15px;
    padding: 27px 30px;
    margin-bottom: 18px;
    min-height: 195px;

    border-left: 7px solid #d9a435;

    background: linear-gradient(
        110deg,
        #121820,
        #29343c,
        #3b3326
    );

    background-position: center;
    background-size: cover;
}

.mine-eyebrow {
    color: #ebbb54;
    font-weight: 800;
    letter-spacing: .12em;
}

.mine-title {
    color: white !important;
    font-size: 2rem;
    font-weight: 800;
    text-shadow: 0 2px 5px #000;
    margin: 8px 0;
}

.mine-subtitle {
    color: #f0e9d9 !important;
    text-shadow: 0 1px 4px #000;
}

.mine-section {
    color: #242f36;
    font-size: 1.45rem;
    font-weight: 800;
    margin: 22px 0 12px;
}

.guide-banner {
    background: #f5e9d0;
    border-left: 4px solid #d9a435;
    padding: 14px;
    border-radius: 9px;
    margin: 14px 0;
}

@media(max-width:750px) {
    .mine-title {
        font-size: 1.4rem;
    }
}

</style>
""", unsafe_allow_html=True)


# MAIN MINING BANNER

def show_banner():
    st.markdown(
        """
<div class="mine-hero">
<div class="mine-eyebrow">

</div>
<div class="mine-title">
Health, Safety &amp; Equipment Portal
</div>
<div class="mine-subtitle">
Operational Monitoring • Worker Safety • Mine Equipment
</div>
</div>
<div style="font-weight:700">
School of Mining Engineering | University of the Witwatersrand
</div>
<p><i>
A centralized digital monitoring platform for operational decision-making.
</i></p>
""",
        unsafe_allow_html=True
    )

# RISK ASSESSMENT CALCULATION

def assess_risk(likelihood, consequence):

    if not (
        isinstance(likelihood, int)
        and isinstance(consequence, int)
        and not isinstance(likelihood, bool)
        and not isinstance(consequence, bool)
        and 1 <= likelihood <= 5
        and 1 <= consequence <= 5
    ):
        raise ValueError(
            "Likelihood and consequence must "
            "be whole numbers from 1 to 5."
        )

    score = likelihood * consequence

    if score <= 4:
        classification = "Low"

    elif score <= 9:
        classification = "Medium"

    elif score <= 16:
        classification = "High"

    else:
        classification = "Critical"

    return score, classification

# DATABASE CONNECTION

@contextmanager
def connect_db():

    connection = sqlite3.connect(
        str(DATABASE),
        timeout=15
    )

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

# CREATE SAFETY INCIDENT DATABASE

def setup_incidents():

    with connect_db() as conn:

        conn.execute("""
        CREATE TABLE IF NOT EXISTS incidents (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            incident_date TEXT NOT NULL,
            incident_time TEXT,
            shift TEXT,
            location TEXT,
            department TEXT,
            incident_type TEXT,
            category TEXT,
            severity TEXT,
            injury_status TEXT,
            lost_time_status TEXT,
            cause TEXT,
            corrective_action TEXT,
            incident_status TEXT,

            likelihood INTEGER,
            consequence INTEGER,
            risk_score INTEGER,
            risk_classification TEXT
        )
        """)

        csv_path = next(
            (
                BASE / name
                for name in (
                    "safety_incidents.csv",
                    "safety_incidents(2).csv"
                )
                if (BASE / name).is_file()
            ),
            None
        )

        if csv_path is None:
            return

        source = pd.read_csv(
            csv_path,
            dtype=str,
            keep_default_na=False
        )

        missing = set(FIELDS) - set(source.columns)

        if missing:

            st.warning(
                "Incident CSV is missing columns: "
                + ", ".join(sorted(missing))
            )

            return

        existing = set(
            conn.execute("""
                SELECT
                    incident_date,
                    incident_time,
                    department,
                    incident_type,
                    location
                FROM incidents
            """).fetchall()
        )

        sql = (
            f"INSERT INTO incidents "
            f"({', '.join(FIELDS)}) "
            f"VALUES ({', '.join(['?'] * len(FIELDS))})"
        )

        for _, row in source.iterrows():

            key = tuple(
                str(row[field]).strip()
                for field in (
                    "incident_date",
                    "incident_time",
                    "department",
                    "incident_type",
                    "location"
                )
            )

            if key in existing:
                continue

            try:

                score, level = assess_risk(
                    int(row["likelihood"]),
                    int(row["consequence"])
                )

            except (ValueError, TypeError):
                continue

            values = {
                field: str(row[field]).strip()
                for field in FIELDS
            }

            values["risk_score"] = score
            values["risk_classification"] = level

            conn.execute(
                sql,
                [values[field] for field in FIELDS]
            )

            existing.add(key)

# LOAD ALL INCIDENT RECORDS

def get_incidents():

    setup_incidents()

    with connect_db() as conn:

        records = pd.read_sql_query(
            """
            SELECT *
            FROM incidents
            ORDER BY id DESC
            """,
            conn
        )

    return records

# SAVE NEW INCIDENT

def save_incident(record):

    setup_incidents()

    score, classification = assess_risk(
        int(record["likelihood"]),
        int(record["consequence"])
    )

    record["risk_score"] = score
    record["risk_classification"] = classification

    sql = (
        f"INSERT INTO incidents "
        f"({', '.join(FIELDS)}) "
        f"VALUES ({', '.join(['?'] * len(FIELDS))})"
    )

    with connect_db() as conn:

        conn.execute(
            sql,
            [record[field] for field in FIELDS]
        )

# SAFETY INCIDENT REPORTING PAGE

def render_incident_reports(role):

    if role not in SAFETY_ROLES:

        st.error(
            "You do not have permission "
            "to view safety incidents."
        )

        return

    st.subheader(
        " Safety Incident Reporting and Analysis"
    )

    st.caption(
        "Educational incident dataset and locally "
        "saved records. Not live mine data."
    )

    records = get_incidents()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Incidents",
        len(records)
    )

    c2.metric(
        "Near Misses",
        int(
            records["category"].eq(
                "Near Miss"
            ).sum()
        )
    )

    c3.metric(
        "High Risks",
        int(
            records["risk_classification"].eq(
                "High"
            ).sum()
        )
    )

    c4.metric(
        "Critical Risks",
        int(
            records["risk_classification"].eq(
                "Critical"
            ).sum()
        )
    )

    tab1, tab2, tab3 = st.tabs([
        "View & Filter",
        "Add Incident",
        "Charts & Reports"
    ])

    
    # VIEW AND FILTER INCIDENTS
  
    with tab1:

        search = st.text_input(
            "Search incident ID, location, "
            "department or incident type"
        )

        department = st.selectbox(
            "Department",
            ["All"] + sorted(
                records["department"]
                .dropna()
                .unique()
                .tolist()
            )
        )

        risk = st.selectbox(
            "Risk Classification",
            [
                "All",
                "Low",
                "Medium",
                "High",
                "Critical"
            ]
        )

        status = st.selectbox(
            "Incident Status",
            ["All"] + sorted(
                records["incident_status"]
                .dropna()
                .unique()
                .tolist()
            )
        )

        filtered = records.copy()

        if search:

            keyword = search.casefold().strip()

            matches = filtered[
                [
                    "id",
                    "location",
                    "department",
                    "incident_type"
                ]
            ].astype(str).apply(
                lambda column:
                column.str.casefold().str.contains(
                    keyword,
                    regex=False
                )
            ).any(axis=1)

            filtered = filtered.loc[matches]

        if department != "All":

            filtered = filtered.loc[
                filtered["department"] == department
            ]

        if risk != "All":

            filtered = filtered.loc[
                filtered["risk_classification"] == risk
            ]

        if status != "All":

            filtered = filtered.loc[
                filtered["incident_status"] == status
            ]

        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Filtered Incidents",
            filtered.to_csv(index=False),
            file_name="filtered_incidents.csv",
            mime="text/csv"
        )

    # ADD NEW SAFETY INCIDENT

    with tab2:

        with st.form(
            "incident_input",
            clear_on_submit=True
        ):

            a, b, c = st.columns(3)

            incident_date = a.date_input(
                "Incident Date"
            )

            incident_time = b.time_input(
                "Incident Time"
            )

            shift = c.selectbox(
                "Shift",
                [
                    "Day",
                    "Afternoon",
                    "Night"
                ]
            )

            a, b = st.columns(2)

            location = a.text_input(
                "Location *"
            )

            department = b.text_input(
                "Department *"
            )

            incident_type = st.text_input(
                "Incident Type *"
            )

            a, b, c = st.columns(3)

            category = a.selectbox(
                "Category",
                [
                    "Injury",
                    "Near Miss",
                    "Unsafe Act",
                    "Other"
                ]
            )

            severity = b.selectbox(
                "Severity",
                [
                    "Minor",
                    "Moderate",
                    "Major",
                    "Critical"
                ]
            )

            incident_status = c.selectbox(
                "Incident Status",
                [
                    "Open",
                    "Under Review",
                    "Closed"
                ]
            )

            a, b = st.columns(2)

            injury_status = a.selectbox(
                "Was Anyone Injured?",
                ["No", "Yes"]
            )

            lost_time_status = b.selectbox(
                "Lost-Time Injury?",
                ["No", "Yes"]
            )

            cause = st.text_area(
                "Cause of Incident"
            )

            corrective_action = st.text_area(
                "Corrective Action"
            )

            a, b = st.columns(2)

            likelihood = a.number_input(
                "Likelihood",
                1,
                5,
                3,
                step=1
            )

            consequence = b.number_input(
                "Consequence",
                1,
                5,
                3,
                step=1
            )

            submit = st.form_submit_button(
                "Save Incident"
            )

        if submit:

            if not all([
                location.strip(),
                department.strip(),
                incident_type.strip()
            ]):

                st.error(
                    "Location, department and "
                    "incident type are required."
                )

            else:

                new_incident = {
                    "incident_date":
                        incident_date.isoformat(),

                    "incident_time":
                        incident_time.strftime("%H:%M"),

                    "shift": shift,

                    "location":
                        location.strip(),

                    "department":
                        department.strip(),

                    "incident_type":
                        incident_type.strip(),

                    "category": category,

                    "severity": severity,

                    "injury_status": injury_status,

                    "lost_time_status":
                        lost_time_status,

                    "cause":
                        cause.strip(),

                    "corrective_action":
                        corrective_action.strip(),

                    "incident_status":
                        incident_status,

                    "likelihood":
                        int(likelihood),

                    "consequence":
                        int(consequence)
                }

                save_incident(new_incident)

                st.success(
                    "Safety incident saved successfully."
                )

                st.rerun()

    # INCIDENT ANALYSIS

    with tab3:

        if records.empty:

            st.info(
                "No incident records available."
            )

        else:

            a, b = st.columns(2)

            with a:

                st.markdown(
                    "**Incidents by Department**"
                )

                st.bar_chart(
                    records["department"].value_counts()
                )

            with b:

                st.markdown(
                    "**Incidents by Risk Classification**"
                )

                st.bar_chart(
                    records[
                        "risk_classification"
                    ].value_counts()
                )

            monthly = records.copy()

            monthly["Month"] = pd.to_datetime(
                monthly["incident_date"],
                errors="coerce"
            ).dt.to_period("M").astype(str)

            st.markdown(
                "**Monthly Incident Trend**"
            )

            st.line_chart(
                monthly.groupby("Month").size()
            )

            st.download_button(
                "Download All Incident Records",
                records.to_csv(index=False),
                file_name="khwezi_incidents.csv",
                mime="text/csv"
            )

# RISK ASSESSMENT PAGE

def render_risk_assessment(role):

    if role not in SAFETY_ROLES:

        st.error(
            "Access denied."
        )

        return

    st.subheader(
        " Mining Risk Assessment"
    )

    st.caption(
        "Risk Score = Likelihood × Consequence. "
        "Educational prototype only."
    )

    c1, c2 = st.columns(2)

    likelihood = c1.number_input(
        "Likelihood (1–5)",
        1,
        5,
        3,
        key="risk_likelihood"
    )

    consequence = c2.number_input(
        "Consequence (1–5)",
        1,
        5,
        3,
        key="risk_consequence"
    )

    score, classification = assess_risk(
        int(likelihood),
        int(consequence)
    )

    st.metric(
        "Risk Score",
        f"{score}/25"
    )

    if classification == "Critical":

        st.error(
            "CRITICAL — Apply controls and "
            "escalate immediately."
        )

    elif classification == "High":

        st.warning(
            "HIGH — Corrective action and "
            "management review needed."
        )

    elif classification == "Medium":

        st.info(
            "MEDIUM — Apply controls "
            "and continue monitoring."
        )

    else:

        st.success(
            "LOW — Maintain existing controls."
        )

    st.write(
        f"**Classification: {classification}**"
    )

    # COMPLETE RISK MATRIX

    st.markdown(
        "#### Complete 5 × 5 Risk Matrix"
    )

    matrix = pd.DataFrame(
        {
            f"Consequence {c}": [
                f"{assess_risk(l, c)[0]}: "
                f"{assess_risk(l, c)[1]}"

                for l in range(1, 6)
            ]

            for c in range(1, 6)
        },

        index=[
            f"Likelihood {l}"
            for l in range(1, 6)
        ]
    )

    st.dataframe(
        matrix,
        use_container_width=True
    )

    st.caption(
        "Low: 1–4 | Medium: 5–9 | "
        "High: 10–16 | Critical: 17–25"
    )

    incidents = get_incidents()

    if not incidents.empty:

        st.markdown(
            "#### Recorded Incident Risks"
        )

        st.bar_chart(
            incidents[
                "risk_classification"
            ].value_counts()
        )

# LOAD EACH GROUP MEMBER'S CODE

def import_render(
    filename,
    function_name,
    role
):

    if not (
        BASE / (filename + ".py")
    ).is_file():

        return False

    try:

        module = importlib.import_module(
            filename
        )

        render_function = getattr(
            module,
            function_name,
            None
        )

        if not callable(render_function):

            st.warning(
                f"{filename}.py needs a "
                f"{function_name}(role) function."
            )

            return False

        render_function(role)

        return True

    except Exception as error:

        st.error(
            f"Error in {filename}.py: {error}"
        )

        return False

# LOAD WORKER SAFETY DATA

def load_workers():

    try:

        module = importlib.import_module(
            "person1_worker_safety_module"
        )

        return pd.DataFrame(
            module.load_workers()
        )

    except (
        ImportError,
        AttributeError,
        OSError,
        ValueError
    ):

        for filename in [
            "workers.csv",
            "workers(1).csv",
            "workers(2).csv"
        ]:

            path = BASE / filename

            if path.is_file():

                return pd.read_csv(path)

    return None

# LOAD EQUIPMENT INFORMATION

def load_equipment():

    try:

        module = importlib.import_module(
            "equipment_module"
        )

        data = pd.DataFrame(
            module.prepare(
                module.load_equipment()
            )
        )

        alerts = module.generate_alerts(
            data
        )

        stats = module.equipment_kpis(
            data,
            alerts
        )

        return data, stats

    except (
        ImportError,
        AttributeError,
        OSError,
        ValueError,
        TypeError,
        KeyError
    ):

        return None, None

# PERSON 1 — FULL WORKER HEALTH AND SAFETY FEATURE

WORKERS_FILE = BASE / "workers.csv"
COLUMNS = ["WorkerID", "Department", "JobRole", "Shift", "PPECompliance",
           "SafetyTraining", "FatigueLevel", "SafetyObservations", "NearMisses",
           "PreviousIncidents"]
ROLE_ACCESS = {"Administrator", "Safety Officer", "Mining Engineer", "Manager"}


def load_worker_records():
    if not WORKERS_FILE.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(WORKERS_FILE, dtype={"WorkerID": str})
    for c in COLUMNS:
        if c not in df.columns:
            raise ValueError(f"workers.csv is missing column: {c}")
    for c in ("FatigueLevel", "SafetyObservations", "NearMisses", "PreviousIncidents"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df


def save_worker_records(df):
    df.to_csv(WORKERS_FILE, index=False)


def classify_worker_risk(ppe, training, fatigue, near_misses, previous_incidents):
    score = 0
    if ppe == "No": score += 4
    if training == "No": score += 3
    if fatigue == 4: score += 2
    elif fatigue == 5: score += 4
    if near_misses >= 2: score += 2
    elif near_misses == 1: score += 1
    if previous_incidents >= 1: score += 1
    return "High" if score >= 8 else "Medium" if score >= 4 else "Low"


def generate_worker_warnings(row):
    warnings = []
    if row["PPECompliance"] == "No": warnings.append("HIGH: PPE non-compliance detected.")
    if row["SafetyTraining"] == "No": warnings.append("WARNING: Safety training is incomplete.")
    if int(row["FatigueLevel"]) == 5: warnings.append("CRITICAL: Very high fatigue level detected.")
    elif int(row["FatigueLevel"]) == 4: warnings.append("WARNING: High fatigue level detected.")
    if int(row["NearMisses"]) >= 2: warnings.append("WARNING: Multiple near misses recorded.")
    elif int(row["NearMisses"]) == 1: warnings.append("NOTICE: A near miss has been recorded.")
    if int(row["SafetyObservations"]) >= 3: warnings.append("NOTICE: Several safety observations require review.")
    if int(row["PreviousIncidents"]) >= 2: warnings.append("WARNING: Worker has multiple previous incidents.")
    return warnings or ["NORMAL: No immediate worker safety warning identified."]


def render_worker_page(role):
    st.title(" Worker Health and Safety Monitoring")
    if role not in ROLE_ACCESS:
        st.error("Access denied. Your role does not have permission to view worker safety data.")
        return
    workers = load_worker_records()
    if not workers.empty:
        workers["RiskLevel"] = workers.apply(lambda r: classify_worker_risk(
            r["PPECompliance"], r["SafetyTraining"], int(r["FatigueLevel"]),
            int(r["NearMisses"]), int(r["PreviousIncidents"])), axis=1)
    count = len(workers)
    ppe = round(100 * (workers["PPECompliance"] == "Yes").sum() / count, 1) if count else 0
    a,b,c,d,e = st.columns(5)
    a.metric("Total Workers", count)
    b.metric("PPE Compliance", f"{ppe:.1f}%")
    c.metric("High Fatigue", int((workers["FatigueLevel"] >= 4).sum()))
    d.metric("Training Incomplete", int((workers["SafetyTraining"] == "No").sum()))
    e.metric("Near Misses", int(workers["NearMisses"].sum()))

    st.subheader("Worker Safety Records")
    st.dataframe(workers, use_container_width=True, hide_index=True)
    st.subheader("Check Individual Worker")
    if count:
        selected = st.selectbox("Select Worker ID", workers["WorkerID"].astype(str).tolist())
        row = workers.loc[workers["WorkerID"].astype(str) == selected].iloc[0]
        st.write(f"Department: **{row['Department']}**")
        st.write(f"Job Role: **{row['JobRole']}**")
        st.write(f"Shift: **{row['Shift']}**")
        st.write(f"Risk Level: **{row['RiskLevel']}**")
        for warning in generate_worker_warnings(row):
            if warning.startswith(("CRITICAL", "HIGH")): st.error(warning)
            elif warning.startswith("WARNING"): st.warning(warning)
            elif warning.startswith("NOTICE"): st.info(warning)
            else: st.success(warning)
    else:
        st.info("No workers added yet.")

    st.subheader("Add Worker Safety Record")
    with st.form("add_worker_form"):
        x,y,z = st.columns(3)
        wid = x.text_input("Worker ID")
        department = y.selectbox("Department", ["Mining", "Engineering", "Safety", "Plant", "Other"])
        job = z.text_input("Job Role")
        x,y,z = st.columns(3)
        shift = x.selectbox("Shift", ["Day", "Night"])
        ppe_ok = y.selectbox("PPE Compliant?", ["Yes", "No"])
        training = z.selectbox("Safety Training Complete?", ["Yes", "No"])
        x,y,z = st.columns(3)
        fatigue = x.slider("Fatigue Level", 1, 5, 2)
        observations = y.number_input("Safety Observations", min_value=0, step=1)
        near_misses = z.number_input("Near Misses", min_value=0, step=1)
        previous = st.number_input("Previous Incidents", min_value=0, step=1)
        submitted = st.form_submit_button("Save Worker Record")
    if submitted:
        wid = wid.strip()
        if not wid:
            st.error("Worker ID cannot be empty.")
        elif wid in workers["WorkerID"].astype(str).values:
            st.error("Worker ID already exists.")
        elif not job.strip():
            st.error("Job role cannot be empty.")
        else:
            record = pd.DataFrame([[wid, department, job.strip(), shift, ppe_ok,
                                    training, fatigue, observations, near_misses, previous]], columns=COLUMNS)
            save_worker_records(pd.concat([workers[COLUMNS], record], ignore_index=True))
            st.success("Worker safety record saved successfully.")
            st.rerun()


# EQUIPMENT MODULE

def render_equipment_page(role):

    if import_render(
        "equipment_page",
        "render_equipment_module",
        role
    ):
        return

    equipment, stats = load_equipment()

    st.subheader("Equipment Monitoring")

    if equipment is None:
        st.warning("Equipment data not found.")
        return

    st.dataframe(
        equipment,
        use_container_width=True,
        hide_index=True
    )


    if stats:

        st.write(
            "**Equipment Summary:**",
            stats
        )

# OPERATIONAL REPORTS


def render_reports(role):

    # Reports include downloads of multiple datasets, so restrict them.
    if role != "Administrator":
        st.error("Access denied. Only an Administrator can access all operational reports.")
        st.stop()

    st.subheader("Operational Reports")

    if (BASE / "person4_dashboard.py").is_file():
        if import_render("person4_dashboard", "render_dashboard", role):
            return

    st.info("Basic operational reports are available below.")

    incidents = get_incidents()
    st.download_button(
        "Download Safety Incidents",
        incidents.to_csv(index=False),
        file_name="khwezi_incidents.csv",
        mime="text/csv"
    )

    workers = load_workers()
    if workers is not None:
        st.download_button(
            "Download Worker Records",
            workers.to_csv(index=False),
            file_name="khwezi_workers.csv",
            mime="text/csv"
        )

    equipment, _ = load_equipment()
    if equipment is not None:
        st.download_button(
            "Download Equipment Records",
            equipment.to_csv(index=False),
            file_name="khwezi_equipment.csv",
            mime="text/csv"
        )

# ROLE-BASED NAVIGATION


def pages_for(role):
    """Return only the pages permitted for the authenticated role."""
    pages = ["View Dashboard"]

    if role in SAFETY_ROLES:
        pages.extend(["Worker Safety Logs", "Incident Reports", "Risk Matrix"])

    if role in EQUIPMENT_ROLES:
        pages.extend([
            "Equipment Telemetry", "Equipment Database", "Condition Monitoring",
            "Equipment Alerts", "Maintenance Schedules", "Equipment Analysis"
        ])

    # This page can download all datasets, so restrict it to administrators.
    if role == "Administrator":
        pages.extend(["Operational Reports", "User Control Panel"])

    return pages


# LOGIN INTERFACE

def load_users():
    """Load demonstration accounts from users.json."""
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as file:
            users = json.load(file)
        return users if isinstance(users, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def render_login():
    show_banner()
    st.subheader("Security & Access Control Gateway")
    st.write("Enter your username and password to continue.")

    with st.form("login_form"):
        username = st.text_input("Username").strip()
        password = st.text_input("Password", type="password")
        clicked = st.form_submit_button("Login")

    if clicked:
        users = load_users()
        if not users:
            st.error("Unable to load users.json. Check that it exists beside app.py and contains valid JSON.")
            return

        user = users.get(username)
        if not isinstance(user, dict) or user.get("password") != password:
            st.error("Invalid username or password.")
            return

        role = user.get("role")
        if role not in ALL_ROLES:
            st.error("This account has an invalid or unsupported role.")
            return

        st.session_state.update(
            auth_token=True,
            id_tag=username,
            tier=role
        )
        st.rerun()

# MAIN DASHBOARD


def render_dashboard(role):
    """Show dashboard metrics appropriate to the current user's role."""
    st.markdown(
        '<div class="mine-section">Role-Based Monitoring Dashboard</div>',
        unsafe_allow_html=True
    )
    st.write(f"Welcome, **{st.session_state.get('id_tag', 'User')}**. Your role is **{role}**.")

    if role in SAFETY_ROLES:
        incidents = get_incidents()
        workers = load_workers()
        st.markdown('<div class="mine-section">Worker Safety Overview</div>', unsafe_allow_html=True)
        a, b, c = st.columns(3)
        a.metric("Total Workers", len(workers) if workers is not None else "No data")
        a_incidents = len(incidents) if incidents is not None else 0
        b.metric("Safety Incidents", a_incidents)
        near_misses = 0
        high_risk = 0
        if incidents is not None and not incidents.empty:
            if "category" in incidents.columns:
                near_misses = int(incidents["category"].astype(str).str.casefold().eq("near miss").sum())
            if "risk_classification" in incidents.columns:
                high_risk = int(incidents["risk_classification"].astype(str).eq("High").sum())
        c.metric("Near Misses", near_misses)
        st.metric("High-Risk Incidents", high_risk)
        if incidents is not None and not incidents.empty:
            with st.expander("Preview Safety Incident Records"):
                st.dataframe(incidents.head(10), hide_index=True, use_container_width=True)

    if role in EQUIPMENT_ROLES:
        equipment, stats = load_equipment()
        st.markdown('<div class="mine-section">Equipment Overview</div>', unsafe_allow_html=True)
        if equipment is None:
            st.info("Equipment data is not available.")
        else:
            availability = stats.get("avg_availability") if isinstance(stats, dict) else None
            critical = stats.get("critical_alerts", "No data") if isinstance(stats, dict) else "No data"
            a, b = st.columns(2)
            a.metric("Equipment Records", len(equipment))
            b.metric("Critical Equipment Alerts", critical)
            if availability is not None:
                st.metric("Average Equipment Availability", f"{float(availability):.1f}%")
            if {"Equipment_ID", "Availability"}.issubset(equipment.columns):
                chart_data = equipment.copy()
                chart_data["Availability"] = pd.to_numeric(chart_data["Availability"], errors="coerce")
                chart_data = chart_data.dropna(subset=["Availability"])
                if not chart_data.empty:
                    chart = alt.Chart(chart_data).mark_bar().encode(
                        x="Equipment_ID:N",
                        y=alt.Y("Availability:Q", scale=alt.Scale(domain=[0, 100])),
                        tooltip=["Equipment_ID:N", "Availability:Q"]
                    ).properties(height=280)
                    st.altair_chart(chart, use_container_width=True)

    if role == "Administrator":
        st.info("As Administrator, you can access both safety and equipment information, plus user and operational reports.")

    st.caption("Demonstration data and local records. Not live mine telemetry.")

# MAIN APPLICATION INTERFACE

def render_main():

    role = st.session_state["tier"]

    # LEFT SIDEBAR NAVIGATION

    with st.sidebar:

        st.markdown(
            "## Navigation Menu"
        )

        st.write(
            f"**User:** "
            f"{st.session_state['id_tag']}"
        )

        st.write(
            f"**Role:** {role}"
        )

        selected = st.selectbox(
            "Select Function",
            pages_for(role)
        )

        if st.button("Log Out"):

            for name in [
                "auth_token",
                "id_tag",
                "tier"
            ]:

                st.session_state.pop(
                    name,
                    None
                )

            st.rerun()

        st.caption(
            "KHWEZI MINING "
        )

    # MAIN BANNER

    show_banner()

    st.divider()

    # CALL DASHBOARD

    if selected == "View Dashboard":

        render_dashboard(role)

    # CALL WORKER SAFETY

    elif selected == "Worker Safety Logs":

        if role not in SAFETY_ROLES:
            st.error("Access denied.")
            st.stop()
        render_worker_page(role)

    # CALL SAFETY INCIDENTS

    elif selected == "Incident Reports":

        if role not in SAFETY_ROLES:
            st.error("Access denied.")
            st.stop()
        render_incident_reports(role)

    # CALL RISK ASSESSMENT

    elif selected == "Risk Matrix":

        if role not in SAFETY_ROLES:
            st.error("Access denied.")
            st.stop()
        render_risk_assessment(role)

    # CALL EQUIPMENT MODULE

    elif selected in {

        "Equipment Telemetry",
        "Equipment Database",
        "Condition Monitoring",
        "Equipment Alerts",
        "Maintenance Schedules",
        "Equipment Analysis"

    }:

        if role not in EQUIPMENT_ROLES:
            st.error("Access denied.")
            st.stop()
        render_equipment_page(role)

    # CALL OPERATIONAL REPORTS

    elif selected == "Operational Reports":

        render_reports(role)

    # CALL USER CONTROL

    elif selected == "User Control Panel":

        if not import_render(
            "user_control",
            "render_user_control",
            role
        ):

            st.info(
                "Upload user_control.py "
                "to enable user management."
            )

# APPLICATION STARTUP

if st.session_state.get(
    "auth_token",
    False
):

    render_main()

else:

    render_login()
