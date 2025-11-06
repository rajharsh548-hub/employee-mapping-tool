# app.py
from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")
# ---------------------------
# Initial users (edit as needed)
# ---------------------------
# Each user can have its own password. Admin is special and can manage users.
USER_CREDENTIALS = {
    "admin@frontlyne.com": "Admin@2025",
    "harsh.a@frontlyne.com": "Harsh@123",
    "alwin.c@frontlyne.com": "Alwin@123"
}

# ---------------------------
# Helper
# ---------------------------
def is_logged_in():
    return "username" in session

def is_admin():
    return session.get("username") == "admin@frontlyne.com"

# ---------------------------
# Routes
# ---------------------------
@app.route("/", methods=["GET"])
def index():
    if is_logged_in():
        return redirect(url_for("upload_page"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            session["username"] = username
            return redirect(url_for("upload_page"))
        else:
            error = "Invalid username or password"
    return render_template("login.html", error=error)

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

# Upload / main page
@app.route("/upload", methods=["GET"])
def upload_page():
    if not is_logged_in():
        return redirect(url_for("login"))
    return render_template("upload.html", username=session.get("username"))

@app.route("/upload", methods=["POST"])
def upload():
    if not is_logged_in():
        return redirect(url_for("login"))

    # Expecting Employee–Store Excel (or CSV). You can adapt to two-file flow later.
    file = request.files.get("file")
    if not file:
        flash("No file uploaded", "error")
        return render_template("upload.html", username=session.get("username"))

    # Basic validation & read
    filename = file.filename.lower()
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(file, dtype=str)
        else:
            df = pd.read_excel(file, dtype=str)
    except Exception as e:
        flash(f"Failed to read file: {e}", "error")
        return render_template("upload.html", username=session.get("username"))

    # Example: validate the required columns exist
    required_cols = ["Employee Code", "Store Code"]
    if not all(col in df.columns for col in required_cols):
        flash(f"File is missing required columns. Required: {required_cols}", "error")
        return render_template("upload.html", username=session.get("username"))

    # Your processing logic (merge, group, etc.) — example groups store codes per employee
    # You can replace this block with the exact logic you used in Colab.
    df_grouped = df.groupby("Employee Code", dropna=False)["Store Code"].apply(lambda x: ",".join(x.astype(str).tolist()) + ",").reset_index()
    # Optional: if you have a user export file to map Full Name, that can be handled in two-file flow.

    # Create Excel to return
    out_wb = Workbook()
    out_ws = out_wb.active
    out_ws.append(["Employee Code", "Store Codes"])
    for _, row in df_grouped.iterrows():
        out_ws.append([row["Employee Code"], row["Store Code"] if "Store Code" in row else row["Store Code"]])
    # Format as text
    for col in out_ws.columns:
        for cell in col:
            cell.number_format = '@'

    virtual_file = BytesIO()
    out_wb.save(virtual_file)
    virtual_file.seek(0)

    return send_file(virtual_file, download_name="Processed_Data.xlsx", as_attachment=True)

# Template download
@app.route("/download-template", methods=["GET"])
def download_template():
    if not is_logged_in():
        return redirect(url_for("login"))
    wb = Workbook()
    ws = wb.active
    ws.title = "Template"
    ws.append(["Employee Code", "Store Code"])
    ws.append(["E001", "S001"])
    ws.append(["E002", "S002"])
    ws.append(["E003", "S003"])
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return send_file(stream, download_name="Employee_Store_Template.xlsx", as_attachment=True)

# Admin panel to view/add/delete users
@app.route("/admin", methods=["GET"])
def admin_panel():
    if not is_logged_in() or not is_admin():
        return redirect(url_for("login"))
    return render_template("admin.html", users=USER_CREDENTIALS)

@app.route("/add-user", methods=["POST"])
def add_user():
    if not is_logged_in() or not is_admin():
        return redirect(url_for("login"))
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if not email or not password:
        flash("Email and password required", "error")
        return redirect(url_for("admin_panel"))
    USER_CREDENTIALS[email] = password
    flash(f"Added user {email}", "success")
    return redirect(url_for("admin_panel"))

@app.route("/delete-user", methods=["POST"])
def delete_user():
    if not is_logged_in() or not is_admin():
        return redirect(url_for("login"))
    email = request.form.get("email", "").strip().lower()
    if email and email in USER_CREDENTIALS and email != "admin@frontlyne.com":
        del USER_CREDENTIALS[email]
        flash(f"Deleted {email}", "success")
    else:
        flash("Cannot delete admin or unknown user", "error")
    return redirect(url_for("admin_panel"))

# Run
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
