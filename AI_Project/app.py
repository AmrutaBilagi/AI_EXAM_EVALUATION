from flask import Flask, render_template, request, redirect, url_for
import os
from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from werkzeug.utils import secure_filename

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
def evaluate_answer(student_text, model_text, total_marks):

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([student_text, model_text])
    similarity = cosine_similarity(
        tfidf_matrix[0:1],
        tfidf_matrix[1:2]
    )[0][0]

    score = round(similarity * total_marks, 2)
    percentage = round(similarity * 100, 2)

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

    return score, percentage, grade, color


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
        total_marks = request.form.get("total_marks")
        file = request.files.get("model_file")

        # Simple password check
        if password != "admin123":
            return "Invalid Password"

        try:
            total_marks = float(total_marks)
        except:
            return "Enter valid total marks"

        if not file or file.filename == "":
            return "Upload Model Answer PDF"

        if not allowed_file(file.filename):
            return "Only PDF files allowed"

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], "model_answer.pdf")
        file.save(filepath)

        model_text = extract_text_from_pdf(filepath)

        if model_text.strip() == "":
            return "Invalid PDF"

        # Save model answer text
        with open("model_answer.txt", "w", encoding="utf-8") as f:
            f.write(model_text)

        # Save total marks
        with open("total_marks.txt", "w") as f:
            f.write(str(total_marks))

        return f"Model Answer Saved Successfully ✅ <br> Welcome {teacher_name}"

    return render_template("teacher.html")

@app.route("/student_login", methods=["GET", "POST"])
def student_login():

    if request.method == "POST":

        file = request.files.get("student_file")

        if not file or file.filename == "":
            return "Upload Answer PDF"

        if not allowed_file(file.filename):
            return "Only PDF allowed"

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
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

        # Load total marks
        try:
            with open("total_marks.txt", "r") as f:
                total_marks = float(f.read())
        except:
            return "Teacher has not set total marks"

        score, percentage, grade, color = evaluate_answer(
            student_text,
            model_text,
            total_marks
        )

        return render_template(
            "result.html",
            score=score,
            percentage=percentage,
            grade=grade,
            color=color
        )

    return render_template("student.html")

# ---------------------------------
# Run App
# ---------------------------------
if __name__ == "__main__":
    app.run(debug=True)