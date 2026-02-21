import PyPDF2
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def extract_text(path):
    text = ""

    with open(path, "rb") as file:
        reader = PyPDF2.PdfReader(file)

        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t

    return text


def similarity_score(student_text, model_text):

    vectorizer = TfidfVectorizer()

    vectors = vectorizer.fit_transform([student_text, model_text])

    score = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]

    return round(score * 100, 2)