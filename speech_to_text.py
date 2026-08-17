# import os
# import whisper
# from dotenv import load_dotenv

# load_dotenv()

# ffmpeg_path = os.getenv("FFMPEG_PATH")

# if ffmpeg_path:
#     os.environ["PATH"] += os.pathsep + ffmpeg_path

# # Load Whisper Tiny model
# model = whisper.load_model("tiny")


# def transcribe_audio(file_path):
#     result = model.transcribe(file_path)
#     return result["text"]


import os
import whisper
from dotenv import load_dotenv

load_dotenv()

ffmpeg_path = os.getenv("FFMPEG_PATH")

if ffmpeg_path:
    os.environ["PATH"] += os.pathsep + ffmpeg_path

model = None


def transcribe_audio(file_path):
    global model

    if model is None:
        model = whisper.load_model("tiny")

    result = model.transcribe(file_path)

    return result["text"]