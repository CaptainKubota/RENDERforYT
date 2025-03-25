from flask import Flask, request, jsonify
import os
import requests
from moviepy.editor import *
import io
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

app = Flask(__name__)

gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

def download_mp3(mp3_url):
    response = requests.get(mp3_url)
    return io.BytesIO(response.content)

def convert_to_mp4(mp3_stream, output_name):
    mp3_stream.seek(0)
    with open("temp.mp3", "wb") as f:
        f.write(mp3_stream.read())

    audio = AudioFileClip("temp.mp3")
    duration = audio.duration
    background = ColorClip(size=(1280, 720), color=(0, 0, 0), duration=duration)
    video = background.set_audio(audio)

    output_file = f"{output_name}.mp4"
    video.write_videofile(output_file, fps=24)
    return output_file

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
    app.run(host="0.0.0.0", port=10000)
