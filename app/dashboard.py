import streamlit as st
import pandas as pd
from app.core.database import SessionLocal
from app.models.models import Task, User, AuditLog, EmailLog
from app.services.ingestion import IngestionService

st.set_page_config(page_title="Cutover Manager Dashboard", layout="wide")

# ------------------------------------------------------------------
# SIDEBAR: DATA INGESTION & MANAGEMENT
# ------------------------------------------------------------------
st.sidebar.title("🎮 Control Panel")
st.sidebar.header("📁 Ingest Schedule")
uploaded_file = st.sidebar.file_uploader("Upload Master Excel", type=["xlsx", "xls"])

# Create an easily accessible DB context helper
db = SessionLocal()

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.sidebar.success(f"Loaded locally: {uploaded_file.name}")
        
        if st.sidebar.button("🚀 Load as Source of Truth", type="primary", use_container_width=True):
            st.sidebar.info("⏳ Synchronizing Postgres tables...")
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                IngestionService.import_tasks_from_excel(temp_path, db)
                st.sidebar.success("🎉 Database Updated Successfully!")
                st.balloons()
            except Exception as d_err:
                st.sidebar.error(f"❌ DB Ingestion Failed: {str(d_err)}")
    except Exception as e:
        st.sidebar.error(f"❌ Error reading file: {str(e)}")

st.sidebar.markdown("---")
st.sidebar.header("⚠️ System Maintenance")

# Dangerous actions wrapped cleanly inside a double-confirmation setup
if st.sidebar.checkbox("Unlock Maintenance Utilities"):
    if st.sidebar.button("🗑️ Wipe All Environment Data", type="secondary", use_container_width=True):
        try:
            db.query(AuditLog).delete()
            db.query(EmailLog).delete()
            db.query(Task).delete()
            db.query(User).delete()
            db.commit()
            st.sidebar.success("💥 Environment wiped clean!")
            st.rerun()
        except Exception as wipe_err:
            db.rollback()
            st.sidebar.error(f"Failed to clear tables: {str(wipe_err)}")

# ------------------------------------------------------------------
# MAIN INTERACTIVE CONSOLE LAYOUT
# ------------------------------------------------------------------
st.title("📋 Cutover Migration Management Console")
st.markdown("Real-time analytical breakdown of ongoing infrastructure shifts and team responsibilities.")

# Pull live database updates for the view layers
try:
    tasks_query = db.query(Task).all()
    users_query = db.query(User).all()
    
    # Convert queries to temporary Pandas layout engines for easy visualization
    all_tasks = [{
        "ID": t.id, "Title": t.title, "Status": t.status, 
        "Assigned ID": t.assigned_to, "Responsible Team": t.responsible_team,
        "Deadline": t.deadline, "Progress": f"{t.actual_percentage or 0}%"
    } for t in tasks_query]
    
    user_map = {u.id: u.email for u in users_query}
    tasks_df = pd.DataFrame(all_tasks)
    
except Exception as read_err:
    st.error(f"Could not reach live database metrics: {str(read_err)}")
    tasks_df = pd.DataFrame()
    user_map = {}

# --- METRIC KPI HEADER ---
if not tasks_df.empty:
    # Map the foreign keys to real owner identities cleanly
    tasks_df["Assigned Owner"] = tasks_df["Assigned ID"].map(user_map)
    
    total_tasks = len(tasks_df)
    pending_tasks = len(tasks_df[tasks_df["Status"].isin(["PENDING", "NOTIFIED"])])
    completed_tasks = len(tasks_df[tasks_df["Status"] == "DONE"])
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📊 Total Actions Scheduled", total_tasks)
    m2.metric("⏳ In-Flight Pipeline Steps", pending_tasks, delta=f"{pending_tasks} Active", delta_color="inverse")
    m3.metric("✅ Completed Migrations", completed_tasks)
    m4.metric("👥 Active Engineers Built", len(user_map))
    
    st.markdown("---")

    # --- FILTERS & SEGMENTATION ROW ---
    st.subheader("🔍 Dynamic Scope Controls")
    f_col1, f_col2 = st.columns(2)
    
    with f_col1:
        selected_status = st.multiselect(
            "Filter Rows by Status Flags:", 
            options=tasks_df["Status"].unique(), 
            default=tasks_df["Status"].unique()
        )
    with f_col2:
        available_owners = [o for o in tasks_df["Assigned Owner"].dropna().unique()]
        selected_owners = st.multiselect(
            "Filter Rows by Responsible Engineer Email:", 
            options=available_owners, 
            default=available_owners
        )
        
    # Apply user runtime view constraints
    filtered_df = tasks_df[
        (tasks_df["Status"].isin(selected_status)) & 
        (tasks_df["Assigned Owner"].isin(selected_owners))
    ]

    # --- TWO COLUMN DATA VIEWS ---
    view_col1, view_col2 = st.columns([3, 2])

    with view_col1:
        st.subheader("📋 Active Work Breakdown Structure")
        display_cols = ["ID", "Title", "Status", "Assigned Owner", "Responsible Team", "Deadline", "Progress"]
        st.dataframe(filtered_df[display_cols], use_container_width=True, hide_index=True)

    with view_col2:
        st.subheader("👥 Workload Distribution Matrix")
        if "Assigned Owner" in filtered_df.columns:
            # Generate a rapid grouping list showing step counts per owner
            distribution = filtered_df["Assigned Owner"].value_counts().reset_index()
            distribution.columns = ["Engineer Email", "Assigned Steps Count"]
            st.dataframe(distribution, use_container_width=True, hide_index=True)
            
            # Show a progress summary group by tech team
            st.markdown("#### Team Action Load")
            team_dist = filtered_df["Responsible Team"].value_counts().reset_index()
            team_dist.columns = ["Engineering Squad", "Total Steps Owned"]
            st.bar_chart(team_dist.set_index("Engineering Squad"))
else:
    # If the database is clean, prompt the manager with a visual indicator
    st.info("💡 There are currently no migration runs registered in the database. Use the sidebar to upload your initial spreadsheet target list.")

db.close()