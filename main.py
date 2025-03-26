from flask import Flask, request, jsonify
import os
import requests
import io
import ffmpeg
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import uuid

app = Flask(__name__)

# Authenticate Google Drive
gauth = GoogleAuth()
gauth.LocalWebserverAuth()  # First time auth; Render will cache creds
drive = GoogleDrive(gauth)

def download_mp3(mp3_url):
    response = requests.get(mp3_url)
    return io.BytesIO(response.content)

def convert_to_mp4(mp3_stream, output_name):
    temp_id = str(uuid.uuid4())
    mp3_path = f"temp_{temp_id}.mp3"
    mp4_path = f"{output_name}.mp4"
    image_path = "background.jpg"

    # Save MP3
    with open(mp3_path, "wb") as f:
        f.write(mp3_stream.read())

    # Ensure background image exists
    if not os.path.exists(image_path):
        # Create a dummy black background image (1280x720)
        from PIL import Image
        img = Image.new("RGB", (1280, 720), color=(0, 0, 0))
        img.save(image_path)

    # Use ffmpeg to combine image and audio
    (
        ffmpeg
        .input(image_path, loop=1)
        .output(mp3_path, shortest=None)
        .run(capture_stdout=True, capture_stderr=True)
    )
    (
        ffmpeg
        .input(image_path, loop=1, framerate=1)
        .output(mp3_path, vcodec='libx264', acodec='aac', strict='experimental', shortest=None, y=mp4_path)
        .run(capture_stdout=True, capture_stderr=True)
    )

    os.remove(mp3_path)
    return mp4_path

def upload_to_drive(mp4_file, folder_name="VideoFiles"):
    folder_list = drive.ListFile({'q': f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder'"}).GetList()
    folder_id = folder_list[0]['id'] if folder_list else None

    if not folder_id:
        folder_metadata = {'title': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = drive.CreateFile(folder_metadata)
        folder.Upload()
        folder_id = folder['id']

    file = drive.CreateFile({'title': os.path.basename(mp4_file), 'parents':[{'id': folder_id}]})
    file.SetContentFile(mp4_file)
    file.Upload()

@app.route("/process", methods=["POST"])
def process():
    data = request.json
    name = os.path.splitext(data['name'])[0]
    try:
        mp3_data = download_mp3(data['url'])
        mp4_file = convert_to_mp4(mp3_data, name)
        upload_to_drive(mp4_file)
        return jsonify({"status": "success", "file": name + ".mp4"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
