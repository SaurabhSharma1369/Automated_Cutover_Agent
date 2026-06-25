import os
import pandas as pd
from flask import Flask, render_template, request, redirect
from app.core.database import SessionLocal
from app.models.models import Task, User
from app.services.ingestion import IngestionService

app = Flask(__name__)

@app.route("/")
def index():
    db = SessionLocal()
    try:
        tasks = db.query(Task).all()
        users = db.query(User).all()
        user_map = {u.id: u.email for u in users}
    except Exception as e:
        print(f"Database Read Error: {e}")
        tasks, user_map = [], {}
    finally:
        db.close()
        
    # By default, pass None for excel_data so the preview tab stays hidden
    return render_template("dashboard.html", tasks=tasks, user_map=user_map, excel_data=None)

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return redirect("/")
        
    file = request.files["file"]
    if file.filename == "":
        return redirect("/")
        
    if file:
        temp_path = f"temp_{file.filename}"
        file.save(temp_path)
        
        db = SessionLocal()
        try:
            # 1. Read EVERY SINGLE column from the sheet for the preview
            df = pd.read_excel(temp_path)
            # Replace any empty/NaN cells with an empty string so they don't print 'nan'
            df = df.where(pd.notnull(df), None)
            excel_records = df.to_dict(orient="records")
            
            # 2. Process and save the rows into your database
            IngestionService.import_tasks_from_excel(temp_path, db)
            
            # 3. Fetch latest data to display on the page
            tasks = db.query(Task).all()
            users = db.query(User).all()
            user_map = {u.id: u.email for u in users}
            
            # Instead of a hard redirect, render the template with the full dataset
            return render_template("dashboard.html", tasks=tasks, user_map=user_map, excel_data=excel_records)
            
        except Exception as e:
            print(f"Ingestion Core Fault: {e}")
            return redirect("/")
        finally:
            db.close()
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501)