from flask import Flask, render_template, request, redirect
import sqlite3
import os
import re
import pdfplumber

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE = "database.db"


# ---------------- DATABASE ---------------- #

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS papers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_pdf TEXT,
        student_pdf TEXT,
        result TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------- PDF READER ---------------- #

def read_pdf(path):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text


# ---------------- QUESTION PARSER ---------------- #

def extract_answers(text):
    """
    Extract answers using question numbers
    Example pattern:
    Q1
    answer text

    Q2
    answer text
    """

    pattern = r'(Q\d+)(.*?)(?=Q\d+|$)'
    matches = re.findall(pattern, text, re.S)

    answers = {}

    for q, ans in matches:
        answers[q.strip()] = ans.strip()

    return answers


# ---------------- EVALUATION ---------------- #

def evaluate(model, student):

    score = 0
    total = len(model)

    report = ""

    for q in model:

        if q in student:

            model_words = set(model[q].lower().split())
            student_words = set(student[q].lower().split())

            common = model_words.intersection(student_words)

            similarity = len(common) / max(len(model_words), 1)

            marks = round(similarity * 10, 2)

            score += marks

            report += f"{q} : {marks}/10\n"

        else:
            report += f"{q} : Not Answered\n"

    final = round(score,2)

    report += f"\nTotal Score : {final} / {total*10}"

    return report


# ---------------- ROUTES ---------------- #

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/teacher", methods=["GET","POST"])
def teacher():

    if request.method == "POST":

        file = request.files["paper"]

        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        c.execute("INSERT INTO papers (teacher_pdf) VALUES (?)",(path,))
        conn.commit()

        conn.close()

        return redirect("/")

    return render_template("teacher.html")


@app.route("/student", methods=["GET","POST"])
def student():

    if request.method == "POST":

        file = request.files["paper"]

        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        c.execute("SELECT id,teacher_pdf FROM papers ORDER BY id DESC LIMIT 1")
        data = c.fetchone()

        paper_id = data[0]
        teacher_pdf = data[1]

        teacher_text = read_pdf(teacher_pdf)
        student_text = read_pdf(path)

        model_answers = extract_answers(teacher_text)
        student_answers = extract_answers(student_text)

        result = evaluate(model_answers, student_answers)

        c.execute("UPDATE papers SET student_pdf=?, result=? WHERE id=?",
                  (path,result,paper_id))

        conn.commit()
        conn.close()

        return redirect("/result")

    return render_template("student.html")


@app.route("/result")
def result():

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("SELECT result FROM papers ORDER BY id DESC LIMIT 1")

    data = c.fetchone()

    conn.close()

    if data:
        res = data[0]
    else:
        res = "No result"

    return render_template("result.html",result=res)


if __name__ == "__main__":
    app.run(debug=True)