from flask import Flask, render_template, request, redirect, url_for
import os
from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from werkzeug.utils import secure_filename
import re

# ---------------------------------
# Create Flask App (VERY IMPORTANT)
# ---------------------------------
app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Create uploads folder if not exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# ---------------------------------
# Check File Type
# ---------------------------------
def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------
# Extract Text From PDF
# ---------------------------------
def extract_text_from_pdf(filepath):
    text = ""
    try:
        reader = PdfReader(filepath)
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content
    except Exception as e:
        print("PDF Error:", e)
        return ""
    return text


# ---------------------------------
# Evaluate Answer
# ---------------------------------


def evaluate_answer(student_text, model_text):

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    # Extract model questions with marks
    model_pattern = r"(Q\d+)\s*\((\d+)\s*Marks\)(.*?)((?=Q\d+\s*\(\d+\s*Marks\))|$)"
    model_matches = re.findall(model_pattern, model_text, re.DOTALL)

    total_score = 0
    total_marks = 0
    results = []

    for question, marks, model_answer, _ in model_matches:

        marks = float(marks)
        total_marks += marks

        # Extract corresponding student answer
        student_pattern = rf"{question}(.*?)((?=Q\d+)|$)"
        student_match = re.search(student_pattern, student_text, re.DOTALL)

        if student_match:
            student_answer = student_match.group(1)

            vectorizer = TfidfVectorizer()
            tfidf = vectorizer.fit_transform([student_answer, model_answer])
            similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]

            score = round(similarity * marks, 2)
        else:
            score = 0

        total_score += score
        results.append((question, score, marks))

    percentage = round((total_score / total_marks) * 100, 2)

    if percentage >= 75:
        grade = "A"
        color = "green"
    elif percentage >= 60:
        grade = "B"
        color = "blue"
    elif percentage >= 40:
        grade = "C"
        color = "orange"
    else:
        grade = "Fail"
        color = "red"

    return total_score, percentage, grade, color, results


# ---------------------------------
# Routes
# ---------------------------------

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/teacher_login", methods=["GET", "POST"])
def teacher_login():

    if request.method == "POST":

        teacher_name = request.form.get("teacher_name")
        teacher_id = request.form.get("teacher_id")
        password = request.form.get("password")
        file = request.files.get("model_file")

        if password != "admin123":
            return "Invalid Password"

        if not file or file.filename == "":
            return "Upload Model Answer PDF"

        if not allowed_file(file.filename):
            return "Only PDF files allowed"

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], "model_answer.pdf")
        file.save(filepath)

        model_text = extract_text_from_pdf(filepath)

        if model_text.strip() == "":
            return "Invalid PDF"

        # Save extracted text
        with open("model_answer.txt", "w", encoding="utf-8") as f:
            f.write(model_text)

        return f"Model Answer Uploaded Successfully ✅ Welcome {teacher_name}"

    return render_template("teacher.html")

@app.route("/student_login", methods=["GET", "POST"])
def student_login():

    if request.method == "POST":

        file = request.files.get("student_file")

        if not file or file.filename == "":
            return "Upload Answer PDF"

        if not allowed_file(file.filename):
            return "Only PDF allowed"

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(file.filename))
        file.save(filepath)

        student_text = extract_text_from_pdf(filepath)

        if student_text.strip() == "":
            return "Invalid PDF"

        # Load model answer
        try:
            with open("model_answer.txt", "r", encoding="utf-8") as f:
                model_text = f.read()
        except:
            return "Teacher has not uploaded model answer"

        # Evaluate
        score, percentage, grade, color, results = evaluate_answer(
            student_text,
            model_text
        )

        return render_template(
            "result.html",
            score=score,
            percentage=percentage,
            grade=grade,
            color=color,
            results=results
        )

    return render_template("student.html")

# ---------------------------------
# Run App
# ---------------------------------
if __name__ == "__main__":
    app.run(debug=True)