import re
from flask import send_file
from PIL import Image
import os
from pyexpat.errors import messages
import sqlite3
import time
from flask import Flask, render_template, request, redirect, session, flash
from gemini_ai import (
    generate_notes,
    generate_quiz,
    generate_flashcards,
    ask_study_assistant
)
from note_evaluator import evaluate_notes
from speech_to_text import transcribe_audio
from youtube_downloader import download_audio
from flask import send_file
from io import BytesIO

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from PIL import Image, ImageDraw, ImageFont
import textwrap
import os

from handwriting import generate_handwritten_notes

from werkzeug.security import generate_password_hash, check_password_hash
from flask import redirect, url_for

app = Flask(__name__)

app.secret_key = "ideaflow_ai_secret_key"


# Create upload folder if not exists
UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)



# ---------------- DATABASE CONNECTION ---------------- #

def get_db():

    conn = sqlite3.connect("users.db")

    conn.row_factory = sqlite3.Row

    return conn



# ---------------- HOME ---------------- #

@app.route("/")
def home():

    return render_template("index.html")

# ---------------- REGISTER ---------------- #

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        # Hash the password before storing it
        hashed_password = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()

        try:

            cursor.execute("""
                INSERT INTO users(name, email, password)
                VALUES (?, ?, ?)
            """, (
                name,
                email,
                hashed_password
            ))

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()
            flash("Email already registered!", "danger")
            return render_template("register.html")

        conn.close()

        return redirect("/login")

    return render_template("register.html")


# ---------------- LOGIN ---------------- #

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]


        conn = get_db()

        cursor = conn.cursor()


        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE email=?
            """,
            (email,)
        )

        user = cursor.fetchone()


        conn.close()



        if user and check_password_hash(user["password"], password):

            session["user"] = email

            return redirect("/dashboard")


        else:

            flash("Invalid email or password!", "danger")
            return redirect("/login")



    return render_template("login.html")



# ---------------- LOGOUT ---------------- #

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")



# ---------------- DASHBOARD ---------------- #

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    # Total lectures uploaded
    cursor.execute("""
        SELECT COUNT(*)
        FROM notes
        WHERE user_email=?
    """, (session["user"],))
    lectures = cursor.fetchone()[0]

    # Total favorite lectures
    cursor.execute("""
        SELECT COUNT(*)
        FROM notes
        WHERE user_email=? AND favorite=1
    """, (session["user"],))
    favorites = cursor.fetchone()[0]

    # Temporary study streak
    streak = 7

    conn.close()

    return render_template(
        "dashboard.html",
        lectures=lectures,
        favorites=favorites,
        streak=streak
    )




# ---------------- UPLOAD ---------------- #

@app.route("/upload", methods=["GET","POST"])
def upload():

    if request.method == "POST":


        file = request.files.get("lecture")

        youtube_link = request.form.get(
            "youtube_link",
            ""
        ).strip()



        upload_path = None


    # File upload

        if file and file.filename:

            lecture_name = file.filename

            upload_path = os.path.join(
                UPLOAD_FOLDER,
                file.filename
            )

            file.save(upload_path)




       # YouTube download


        elif youtube_link:

            upload_path = download_audio(
                youtube_link
            )

            if upload_path is None:

                flash(
                    "❌ Unable to download the YouTube video. Please check that the link is valid and the video is public.",
                    "danger"
                )

                return render_template("upload.html")

            lecture_name = os.path.basename(upload_path)

            


# Nothing selected

        else:

            return "Please upload a file or provide a YouTube link."
        

        # Speech to text

        start = time.time()


        transcript = transcribe_audio(
            upload_path
        )


        print(
            "Whisper Time:",
            time.time()-start
        )




        

        # Generate Notes

        start = time.time()

        notes = generate_notes(
            transcript
        )

        print(
            "Gemini Time:",
            time.time() - start
        )

        # Evaluate Notes
        evaluation = evaluate_notes(
            transcript,
            notes
        )

        print("\n===== NOTE EVALUATION =====")
        print(evaluation)
        print("===========================\n")

        # Generate Quiz
        quiz = generate_quiz(transcript)

        # Generate Flashcards
        flashcards = generate_flashcards(transcript)

        print(
            "Gemini Time:",
            time.time()-start
        )



        # Save notes


        conn = get_db()

        cursor = conn.cursor()



        cursor.execute(
            """
            INSERT INTO notes
            (
            user_email,
            transcript,
            ai_notes,
            lecture_name
            )
         VALUES(?,?,?,?)
            """,
            (
                session.get(
                    "user",
                    "guest"
                ),
                transcript,
                notes,
                lecture_name
            )
        )


        note_id = cursor.lastrowid
        # Save Quiz
        cursor.execute(
            """
            INSERT INTO quizzes
            (
                note_id,
                quiz
            )
            VALUES (?, ?)
            """,
            (
                note_id,
                quiz
            )
        )

        # Save Flashcards
        cursor.execute(
            """
            INSERT INTO flashcards
            (
                note_id,
                flashcards
            )
            VALUES (?, ?)
            """,
            (
                note_id,
                flashcards
            )
        )

        conn.commit()

        conn.close()



        flash("🎉 AI Notes generated successfully!", "success")
        return redirect(f"/note/{note_id}")



    return render_template("upload.html")



# ---------------- NOTES HISTORY ---------------- #

@app.route("/notes")
def notes_history():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    search = request.args.get("search", "").strip()

    if search:

        cursor.execute("""
            SELECT id, lecture_name, favorite, created_at
            FROM notes
            WHERE user_email=? AND lecture_name LIKE ?
            ORDER BY created_at DESC
        """, (
            session["user"],
            f"%{search}%"
        ))

    else:

        cursor.execute("""
            SELECT id, lecture_name, favorite, created_at
            FROM notes
            WHERE user_email=?
            ORDER BY created_at DESC
        """, (
            session["user"],
        ))

    notes = cursor.fetchall()

    conn.close()

    return render_template(
        "notes_history.html",
        notes=notes
    )



# ---------------- VIEW NOTE ---------------- #

@app.route("/note/<int:note_id>")
def view_note(note_id):


    conn=get_db()

    cursor=conn.cursor()


    cursor.execute(
        """
        SELECT transcript,
               ai_notes,
               created_at
        FROM notes
        WHERE id=?
        """,
        (note_id,)
    )


    note=cursor.fetchone()


    conn.close()



    if not note:

        return "Note not found."



    return render_template(
    "view_note.html",
    transcript=note["transcript"],
    notes=note["ai_notes"],
    created_at=note["created_at"],
    note_id=note_id
    )

# ---------------- HANDWRITTEN NOTES ---------------- #

@app.route("/handwritten/<int:note_id>")
def handwritten(note_id):

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ai_notes
        FROM notes
        WHERE id=?
    """, (note_id,))

    note = cursor.fetchone()

    conn.close()

    if not note:
        return "Note not found."

    output_folder = "static/handwritten"

    generate_handwritten_notes(
        note["ai_notes"],
        output_folder,
        f"note_{note_id}"
    )

    pages = sorted([
        file for file in os.listdir(output_folder)
        if file.startswith(f"note_{note_id}_page")
    ])

    return render_template(
        "handwritten.html",
        pages=pages,
        note_id=note_id
    )

@app.route("/download_handwritten_pdf/<int:note_id>")
def download_handwritten_pdf(note_id):

    if "user" not in session:
        return redirect("/login")

    folder = "static/handwritten"

    pages = sorted([
        os.path.join(folder, file)
        for file in os.listdir(folder)
        if file.startswith(f"note_{note_id}_page")
    ])

    if not pages:
        return "No handwritten pages found."

    images = [Image.open(page).convert("RGB") for page in pages]

    pdf_path = os.path.join(folder, f"note_{note_id}.pdf")

    images[0].save(
        pdf_path,
        save_all=True,
        append_images=images[1:]
    )

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=f"Handwritten_Notes_{note_id}.pdf"
    )

# ---------------- DELETE NOTE ---------------- #

@app.route("/delete_note/<int:note_id>")
def delete_note(note_id):


    conn=get_db()

    cursor=conn.cursor()


    cursor.execute(
        """
        DELETE FROM notes
        WHERE id=?
        """,
        (note_id,)
    )


    conn.commit()

    conn.close()


    return redirect("/notes")





    # ---------------- PARSE QUIZ ---------------- #


def parse_quiz(quiz_text):
    quiz_data = []

    blocks = quiz_text.strip().split("Question:")

    for block in blocks:
        block = block.strip()

        if not block:
            continue

        lines = [
            line.strip()
            for line in block.splitlines()
            if line.strip()
        ]

        if len(lines) < 6:
            continue

        question = lines[0]

        options = [
            lines[1],
            lines[2],
            lines[3],
            lines[4]
        ]

        answer_line = lines[5]

        correct_letter = (
            answer_line
            .replace("Answer:", "")
            .strip()
            .upper()
        )

        correct_option = ""

        for option in options:
            if option.upper().startswith(correct_letter):
                correct_option = option
                break

        quiz_data.append({
            "question": question,
            "options": options,
            "answer": correct_option,
            "answer_letter": correct_letter
        })

    return quiz_data

# ---------------- QUIZ ---------------- #

@app.route("/quiz/<int:note_id>")
def quiz(note_id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT quiz
        FROM quizzes
        WHERE note_id=?
        """,
        (note_id,)
    )

    existing = cursor.fetchone()

    if existing:

        quiz_text = existing["quiz"]

    else:

        cursor.execute(
            """
            SELECT transcript
            FROM notes
            WHERE id=?
            """,
            (note_id,)
        )

        note = cursor.fetchone()

        if not note:
            conn.close()
            return "Note not found."

        quiz_text = generate_quiz(note["transcript"])

        print("GENERATED QUIZ:")
        print(quiz_text)

        cursor.execute(
            """
            INSERT INTO quizzes
            (
                note_id,
                quiz
            )
            VALUES (?, ?)
            """,
            (
                note_id,
                quiz_text
            )
        )

        conn.commit()

    conn.close()

    # Parse quiz using ONE common parser
    quiz_data = parse_quiz(quiz_text)

    print("PARSED QUIZ DATA:")
    print(quiz_data)

    return render_template(
        "quiz.html",
        quiz_data=quiz_data
    )

    # -------------------------------
    # Convert quiz text into questions
    # -------------------------------

    questions = []

    pattern = r"\*\*(.*?)\*\*\s*A\)\s*(.*?)\s*B\)\s*(.*?)\s*C\)\s*(.*?)\s*D\)\s*(.*?)\s*\*\*Correct Answer:\s*([A-D])\)\s*(.*?)\*\*"

    matches = re.findall(
        pattern,
        quiz_text,
        re.DOTALL
    )

    for match in matches:

        question = match[0].strip()

        options = [
            "A) " + match[1].strip(),
            "B) " + match[2].strip(),
            "C) " + match[3].strip(),
            "D) " + match[4].strip()
        ]

        correct = match[5].strip()

        questions.append({

            "question": question,

            "options": options,

            "correct": correct

        })

    return render_template(

        "quiz.html",

        questions=questions

    )



# ---------------- QUIZ HISTORY ---------------- #

@app.route("/quiz_history")
def quiz_history():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT q.id,
               q.note_id,
               q.created_at
        FROM quizzes q
        JOIN notes n
            ON q.note_id = n.id
        WHERE n.user_email = ?
        ORDER BY q.created_at DESC
    """, (session["user"],))

    quizzes = cursor.fetchall()

    conn.close()

    return render_template(
        "quizzes.html",
        quizzes=quizzes
    )



# ---------------- VIEW QUIZ ---------------- #

@app.route("/view_quiz/<int:quiz_id>")
def view_quiz(quiz_id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT quiz
        FROM quizzes
        WHERE id=?
        """,
        (quiz_id,)
    )

    row = cursor.fetchone()

    conn.close()

    if not row:
        return "Quiz not found."

    quiz_text = row["quiz"]

    # Use the SAME parser used by /quiz/<note_id>
    quiz_data = parse_quiz(quiz_text)

    print("VIEW QUIZ ID:", quiz_id)
    print("QUIZ TEXT:")
    print(quiz_text)
    print("PARSED DATA:")
    print(quiz_data)

    return render_template(
        "quiz.html",
        quiz_data=quiz_data
    )



# ---------------- FLASHCARDS ---------------- #

@app.route("/flashcards/<int:note_id>")
def flashcards(note_id):


    conn=get_db()

    cursor=conn.cursor()



    cursor.execute(
        """
        SELECT flashcards
        FROM flashcards
        WHERE note_id=?
        """,
        (note_id,)
    )


    existing=cursor.fetchone()



    if existing:


        conn.close()


        return render_template(
            "flashcards.html",
            flashcards=existing["flashcards"]
        )



    cursor.execute(
        """
        SELECT transcript
        FROM notes
        WHERE id=?
        """,
        (note_id,)
    )


    note=cursor.fetchone()



    if not note:

        conn.close()

        return "Note not found."



    cards=generate_flashcards(
        note["transcript"]
    )



    cursor.execute(
        """
        INSERT INTO flashcards
        (
        note_id,
        flashcards
        )
        VALUES(?,?)
        """,
        (
            note_id,
            cards
        )
    )


    conn.commit()

    conn.close()



    return render_template(
        "flashcards.html",
        flashcards=cards
    )

# ---------------- FLASHCARD HISTORY ---------------- #

@app.route("/flashcards_history")
def flashcards_history():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT f.id,
               f.note_id,
               f.created_at
        FROM flashcards f
        JOIN notes n
            ON f.note_id = n.id
        WHERE n.user_email = ?
        ORDER BY f.created_at DESC
    """, (session["user"],))

    flashcards = cursor.fetchall()

    conn.close()

    return render_template(
        "flashcards_library.html",
        flashcards=flashcards
    )



# ---------------- VIEW FLASHCARDS ---------------- #

@app.route("/view_flashcards/<int:flashcard_id>")
def view_flashcards(flashcard_id):


    conn = get_db()

    cursor = conn.cursor()


    cursor.execute(
        """
        SELECT flashcards
        FROM flashcards
        WHERE id=?
        """,
        (flashcard_id,)
    )


    cards = cursor.fetchone()


    conn.close()


    if not cards:

        return "Flashcards not found."



    return render_template(
        "flashcards.html",
        flashcards=cards["flashcards"]
    )

# ---------------- LIBRARY ---------------- #

@app.route("/library")
def library():

    return render_template(
        "library.html"
    )

# ---------------- AI STUDY ASSISTANT ---------------- #

@app.route("/chat", methods=["GET", "POST"])
def chat():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    # Get all lectures of current user
    cursor.execute("""
        SELECT id, lecture_name
        FROM notes
        WHERE user_email=?
        ORDER BY created_at DESC
    """, (session["user"],))

    lectures = cursor.fetchall()

    if "chat_history" not in session:
        session["chat_history"] = []

    messages = session["chat_history"]

    selected_note = None

    if request.method == "POST":

        selected_note = request.form["note_id"]
        if session.get("selected_note") != selected_note:
            session["chat_history"] = []
            session["selected_note"] = selected_note
            messages = session["chat_history"]
        question = request.form["question"]

        cursor.execute("""
            SELECT ai_notes
            FROM notes
            WHERE id=?
        """, (selected_note,))

        note = cursor.fetchone()

        if note:

            answer = ask_study_assistant(
                note["ai_notes"],
                question,
                messages
            )

        else:

            answer = "Lecture not found."

        messages.append({
            "role": "user",
            "content": question
        })

        messages.append({
            "role": "ai",
            "content": answer
        })

        session["chat_history"] = messages
        session.modified = True

    conn.close()

    return render_template(
        "chat.html",
        lectures=lectures,
        messages=messages,
        selected_note=selected_note
    )

# ---------------- ANALYTICS ---------------- #

from datetime import datetime, timedelta

# ---------------- ANALYTICS ---------------- #

@app.route("/analytics")
def analytics():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    # Total lectures
    cursor.execute("""
        SELECT COUNT(*)
        FROM notes
        WHERE user_email=?
    """, (session["user"],))
    lectures = cursor.fetchone()[0]

    # Total notes
    notes = lectures

    
    # Total quizzes
# Total quizzes (current user only)
    cursor.execute("""
        SELECT COUNT(*)
        FROM quizzes q
        JOIN notes n
            ON q.note_id = n.id
        WHERE n.user_email = ?
    """, (session["user"],))

    quizzes = cursor.fetchone()[0]

    # Total flashcards (current user only)
    # Total flashcards (current user only)
    cursor.execute("""
        SELECT COUNT(*)
        FROM flashcards f
        JOIN notes n
            ON f.note_id = n.id
        WHERE n.user_email = ?
    """, (session["user"],))

    flashcards = cursor.fetchone()[0]

    # Study Streak
    cursor.execute("""
        SELECT DATE(created_at)
        FROM notes
        WHERE user_email=?
        ORDER BY created_at DESC
    """, (session["user"],))

    dates = [row[0] for row in cursor.fetchall()]

    streak = 0
    current = datetime.now().date()

    unique_dates = sorted(set(dates), reverse=True)

    for d in unique_dates:
        if str(current) == d:
            streak += 1
            current = current - timedelta(days=1)
        else:
            break

    conn.close()

    return render_template(
        "analytics.html",
        lectures=lectures,
        notes=notes,
        quizzes=quizzes,
        flashcards=flashcards,
        streak=streak
    )

# ---------------- FAVOURITE NOTE ---------------- #

@app.route("/favorite_note/<int:note_id>")
def favorite_note(note_id):

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE notes
        SET favorite = CASE
            WHEN favorite = 0 THEN 1
            ELSE 0
        END
        WHERE id=?
    """, (note_id,))

    conn.commit()
    conn.close()

    return redirect("/notes")

# ---------------- DOWNLOAD PDF ---------------- #

@app.route("/download_pdf/<int:note_id>")
def download_pdf(note_id):

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT lecture_name, ai_notes
        FROM notes
        WHERE id=? AND user_email=?
    """, (note_id, session["user"]))

    note = cursor.fetchone()

    conn.close()

    if not note:
        return "Note not found."

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    story = []

    story.append(Paragraph("<b>IdeaFlow AI Notes</b>", styles["Heading1"]))
    story.append(Paragraph(f"<b>Lecture:</b> {note['lecture_name']}", styles["Normal"]))
    story.append(Paragraph("<br/>", styles["Normal"]))
    story.append(Paragraph(note["ai_notes"].replace("\n", "<br/>"), styles["Normal"]))

    doc.build(story)

    buffer.seek(0)

    filename = f"{note['lecture_name']}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )

# ---------------- VOICE ASSISSTANT ---------------- #

@app.route("/voice-assistant")
def voice_assistant():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, lecture_name
        FROM notes
        WHERE user_email=?
        ORDER BY created_at DESC
    """, (session["user"],))

    lectures = cursor.fetchall()

    conn.close()

    return render_template(
        "voice_assistant.html",
        lectures=lectures
    )

# ---------------- VOICE CHAT ---------------- #

@app.route("/voice-chat", methods=["POST"])
def voice_chat():

    if "user" not in session:
        return {"answer": "Please login first."}

    note_id = request.form["note_id"]
    question = request.form["question"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ai_notes
        FROM notes
        WHERE id=?
    """, (note_id,))

    note = cursor.fetchone()

    conn.close()

    if not note:
        return {"answer": "Lecture not found."}

    answer = ask_study_assistant(
        note["ai_notes"],
        question
    )

    return {
        "answer": answer
    }

# ---------------- SETTINGS ---------------- #

@app.route("/settings")
def settings():

    if "user" not in session:
        flash("Password updated successfully!", "success")
        return redirect("/settings")

    return render_template("settings.html")

# ---------------- CHANGE NAME ---------------- #

@app.route("/change-name", methods=["GET", "POST"])
def change_name():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":

        new_name = request.form["name"]

        cursor.execute("""
            UPDATE users
            SET name=?
            WHERE email=?
        """, (
            new_name,
            session["user"]
        ))

        conn.commit()
        conn.close()

        return redirect("/settings")

    conn.close()

    return render_template("change_name.html")

# ---------------- CHANGE PASSWORD ---------------- #

@app.route("/change-password", methods=["GET", "POST"])
def change_password():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":

        current_password = request.form["current_password"]
        new_password = request.form["new_password"]

        cursor.execute("""
            SELECT password
            FROM users
            WHERE email=?
        """, (session["user"],))

        user = cursor.fetchone()

        if not check_password_hash(user["password"], current_password):

            conn.close()
            flash("Current password is incorrect!", "danger")
            return redirect("/change-password")

        new_hashed_password = generate_password_hash(new_password)

        cursor.execute("""
            UPDATE users
            SET password=?
            WHERE email=?
        """, (
            new_hashed_password,
            session["user"]
        ))

        conn.commit()
        conn.close()

        return redirect("/settings")

    conn.close()

    return render_template("change_password.html")

# ---------------- RUN ---------------- #

if __name__=="__main__":

    app.run(
        debug=True
    )