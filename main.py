from flask import Flask, request, jsonify
import os
import requests
from moviepy.editor import AudioFileClip, ImageClip, ColorClip
import io
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Authenticate Google Drive
gauth = GoogleAuth()
try:
    # Use saved credentials if available, otherwise authenticate
    gauth.LoadCredentialsFile("mycreds.txt")
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()  # Opens browser for first-time auth
        gauth.SaveCredentialsFile("mycreds.txt")
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
except Exception as e:
    logger.error(f"Google Drive auth failed: {e}")
drive = GoogleDrive(gauth)

def download_mp3(mp3_url):
    logger.info(f"Downloading MP3 from {mp3_url}")
    response = requests.get(mp3_url, timeout=10)
    response.raise_for_status()  # Raise exception for bad HTTP status
    return io.BytesIO(response.content)

def convert_to_mp4(mp3_stream, output_name):
    logger.info("Converting MP3 to MP4")
    mp3_stream.seek(0)
    with open("temp.mp3", "wb") as f:
        f.write(mp3_stream.read())

    try:
        audio = AudioFileClip("temp.mp3")
        duration = audio.duration
        logger.info(f"Audio duration: {duration}s")
    except Exception as e:
        logger.error(f"Failed to load audio: {e}")
        raise

    # Optional: use a static image if you upload one as background.jpg
    if os.path.exists("background.jpg"):
        image_clip = ImageClip("background.jpg", duration=duration)
    else:
        image_clip = ColorClip(size=(1280, 720), color=(0, 0, 0), duration=duration)

    video = image_clip.set_audio(audio)
    output_file = f"{output_name}.mp4"
    try:
        video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac")
        logger.info(f"Video written to {output_file}")
    except Exception as e:
        logger.error(f"MoviePy failed: {e}")
        raise

    if os.path.exists("temp.mp3"):
        os.remove("temp.mp3")
    return output_file

def upload_to_drive(mp4_file, folder_name="VideoFiles"):
    logger.info(f"Uploading {mp4_file} to Google Drive")
    try:
        folder_list = drive.ListFile({'q': f"title='{folder_name}' mimeType='application/vnd.google-apps.folder'"}).GetList()
        folder_id = folder_list[0]['id'] if folder_list else None

        if not folder_id:
            folder_metadata = {'title': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
            folder = drive.CreateFile(folder_metadata)
            folder.Upload()
            folder_id = folder['id']

        file = drive.CreateFile({'title': os.path.basename(mp4_file), 'parents': [{'id': folder_id}]})
        file.SetContentFile(mp4_file)
        file.Upload()
        logger.info("Upload complete")
    except Exception as e:
        logger.error(f"Drive upload failed: {e}")
        raise

@app.route("/process", methods=["POST"])
def process():
    data = request.json
    if not data or 'url' not in data or 'name' not in data:
        return jsonify({"status": "error", "message": "Missing url or name"}), 400

    name = os.path.splitext(data['name'])[0]
    try:
        mp3_data = download_mp3(data['url'])
        mp4_file = convert_to_mp4(mp3_data, name)
        upload_to_drive(mp4_file)
        return jsonify({"status": "success", "file": name + ".mp4"})
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)