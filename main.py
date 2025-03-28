from flask import Flask
import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import ffmpeg

app = Flask(__name__)

# Google Drive authentication with service account
gauth = GoogleAuth()
gauth.credentials = GoogleAuth().ServiceAccountCredentials.from_json_keyfile_name('service_account.json')
drive = GoogleDrive(gauth)

INPUT_FOLDER_ID = "your_input_folder_id"
OUTPUT_FOLDER_ID = "your_output_folder_id"
STATIC_IMAGE = "static.jpg"

def process_audio_to_video():
    file_list = drive.ListFile({'q': f"'{INPUT_FOLDER_ID}' in parents and trashed=false"}).GetList()
    for file in file_list:
        if file['title'].endswith('.mp3'):
            mp3_file = file['title']
            mp4_file = mp3_file.replace('.mp3', '.mp4')
            file.GetContentFile(mp3_file)
            try:
                stream = ffmpeg.input(STATIC_IMAGE)
                stream = ffmpeg.input(mp3_file).output(stream, mp4_file, c='copy', shortest=True, vcodec='libx264', acodec='aac')
                ffmpeg.run(stream)
            except ffmpeg.Error as e:
                print(f"FFmpeg error: {e.stderr.decode()}")
                return
            upload_file = drive.CreateFile({'title': mp4_file, 'parents': [{'id': OUTPUT_FOLDER_ID}]})
            upload_file.SetContentFile(mp4_file)
            upload_file.Upload()
            os.remove(mp3_file)
            os.remove(mp4_file)

@app.route('/')
def run_process():
    process_audio_to_video()
    return "Conversion complete!"

if __name__ == '__main__':
    app.run(debug=True)