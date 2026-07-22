import os
from dotenv import load_dotenv
from google import genai

# Load variables from .env
load_dotenv()

# Read API key
api_key = os.getenv("GEMINI_API_KEY")

# Create Gemini client
client = genai.Client(api_key=api_key)


# ---------------- AI NOTES ---------------- #

def generate_notes(text):

    prompt = f"""
You are an AI Study Assistant.

Convert the following lecture into professional study notes.

Requirements:
- Use clear headings
- Use bullet points
- Highlight important concepts
- Keep the language simple
- Make notes suitable for exam preparation

Lecture:
{text}
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
    )

    return response.text


# ---------------- AI QUIZ ---------------- #

def generate_quiz(text):

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=f"""
Generate exactly 5 multiple choice questions from this lecture.

Format exactly like this:

Question: What is Java?
A) Programming language
B) Database
C) Operating System
D) Browser
Answer: A

Lecture:
{text}
"""
    )

    print(response.text)

    return response.text

# ---------------- AI FLASHCARDS ---------------- #

def generate_flashcards(text):

    prompt = f"""
You are an expert teacher.

Create study flashcards from this lecture.

Format EXACTLY like this:

Requirements:

- Create at least 10 flashcards.

Format EXACTLY like this:

Q: What is Artificial Intelligence?
A: Artificial Intelligence is the simulation of human intelligence by machines.

Q: What is Machine Learning?
A: Machine Learning is a subset of Artificial Intelligence.

IMPORTANT:
- Do NOT leave a blank line between Q: and A:.
- Q: and A: must always be consecutive lines.
- Leave exactly ONE blank line after each flashcard.
- Never separate a question from its answer.

Lecture:
{text}
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
    )

    return response.text

# ---------------- AI STUDY ASSISTANT ---------------- #

def ask_study_assistant(notes, question, history=None):

    conversation = ""

    if history:

        for message in history:

            if message["role"] == "user":

                conversation += f"Student: {message['content']}\n"

            else:

                conversation += f"AI: {message['content']}\n"


    prompt = f"""
You are IdeaFlow AI, an intelligent Study Assistant.

Use ONLY the lecture notes below.

If the student asks a follow-up question,
use the previous conversation for context.

If the answer is not available in the lecture,
politely say you cannot find it.

Lecture Notes:
{notes}

Previous Conversation:
{conversation}

Current Student Question:
{question}
"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
    )

    return response.text