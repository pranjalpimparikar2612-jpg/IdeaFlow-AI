# import os
# import yt_dlp


# def download_audio(youtube_url):

#     output_path = "uploads"

#     ydl_opts = {
#         "format": "bestaudio/best",
#         "outtmpl": os.path.join(output_path, "%(title)s.%(ext)s"),
#         "quiet": True,
#         "noplaylist": True,
#     }

#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:

#         info = ydl.extract_info(youtube_url, download=True)

#         filename = ydl.prepare_filename(info)

#     return filename

import yt_dlp
import os

def download_audio(youtube_url):

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "uploads/%(title)s.%(ext)s",
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            return ydl.prepare_filename(info)

    except Exception:
        return None