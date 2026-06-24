import pandas as pd
from datetime import datetime, timedelta

# All 26 unique columns you provided in your layout sequence
columns = [
    "Task Name", "Planned % Complete", "Actual % Complete", "Start Date", "End Date", 
    "Responsible Team", "Assigned To", "Secondary Owner", "Duration", "Time", 
    "Status", "Cancel Flag", "Weekly Report", "At Risk", "Delayed", "Description", 
    "Actual End Date", "data", "Delay Reason", "Recovery", "Recovery Date", 
    "Predecessors", "Level", "Baseline Start", "Baseline Finish", "Variance"
]

# Generate dummy test rows using your active testing email profiles
dummy_rows = [
    {
        "Task Name": "Database Schema Hotfix Update",
        "Planned % Complete": "100%",
        "Actual % Complete": "0%",
        "Start Date": datetime.utcnow().date(),
        "End Date": (datetime.utcnow() - timedelta(days=2)).date(), # Expired deadline
        "Responsible Team": "Backend Core",
        "Assigned To": "jsking982@gmail.com",
        "Secondary Owner": "jsking981@gmail.com",
        "Duration": "2h",
        "Time": "14:30:00",
        "Status": "PENDING",
        "Cancel Flag": "No",
        "Description": "Running column migrations on live Postgres engine clusters."
    },
    {
        "Task Name": "Frontend UI Assets Compilation",
        "Planned % Complete": "100%",
        "Actual % Complete": "100%",
        "Start Date": datetime.utcnow().date(),
        "End Date": (datetime.utcnow() + timedelta(days=2)).date(), # Future deadline
        "Responsible Team": "UI Platform",
        "Assigned To": "jsking982@gmail.com",
        "Secondary Owner": "jitendras.ug23.cs@nitp.ac.in",
        "Duration": "1h",
        "Time": "09:00:00",
        "Status": "DONE",
        "Cancel Flag": "No",
        "Description": "Building production bundles for user dashboard layout grids."
    }
]

# Build the structured dataframe mapping
df = pd.DataFrame(dummy_rows, columns=columns)

# Save out to your root project workspace
output_name = "cutover_master.xlsx"
df.to_excel(output_name, index=False)
print(f"📊 Perfect dummy sheet created successfully at: {output_name}")