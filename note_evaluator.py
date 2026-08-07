from gemini_ai import client   # or wherever your Gemini client is created

def evaluate_notes(transcript, notes):

    prompt = f"""
You are an expert teacher.

Compare the lecture transcript with the generated notes.

Transcript:
{transcript}

Notes:
{notes}

Evaluate them based on:

1. Accuracy (0-10)
2. Coverage (0-10)
3. Clarity (0-10)

Return only this format:

Accuracy: X/10
Coverage: X/10
Clarity: X/10

Feedback:
...
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text