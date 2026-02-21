from flask import Flask, render_template, request
import sqlite3
import os
from model import extract_text, similarity_score

app = Flask(__name__)

# ---------------- PATH SETUP ---------------- #

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DB_PATH = "database.db"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# create uploads folder
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------- DATABASE ---------------- #

def init_db():

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS model_answers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        filepath TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------- ROUTES ---------------- #

@app.route("/")
def home():
    return render_template("home.html")


# ---------- TEACHER ---------- #

@app.route("/teacher")
def teacher():
    return render_template("teacher.html")


@app.route("/upload_model", methods=["POST"])
def upload_model():

    question = request.form["question"]
    file = request.files["file"]

    if file.filename == "":
        return "No file selected"

    path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(path)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO model_answers(question, filepath) VALUES (?,?)",
        (question, path)
    )

    conn.commit()
    conn.close()

    return "Model Answer Uploaded Successfully"


# ---------- STUDENT ---------- #

@app.route("/student")
def student():
    return render_template("student.html")


@app.route("/evaluate", methods=["POST"])
def evaluate():

    question = request.form["question"]
    file = request.files["file"]

    if file.filename == "":
        return "Upload answer sheet"

    student_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(student_path)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "SELECT filepath FROM model_answers WHERE question=? ORDER BY id DESC LIMIT 1",
        (question,)
    )

    row = cur.fetchone()
    conn.close()

    if not row:
        return "No model answer found for this question"

    model_path = row[0]

    # AI evaluation
    student_text = extract_text(student_path)
    model_text = extract_text(model_path)

    score = similarity_score(student_text, model_text)

    return render_template("result.html", score=score, question=question)


# ---------------- RUN ---------------- #

if __name__ == "__main__":
    app.run(debug=True)