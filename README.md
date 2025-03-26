# MP3 to MP4 Converter Server (FFmpeg version)

## What This Does

- Receives webhook requests from Google Apps Script
- Downloads MP3 files from Google Drive
- Converts them to MP4 using ffmpeg-python with a black background
- Uploads them to your VideoFiles folder in Drive

## Setup Steps

1. Deploy this repo to [Render.com](https://render.com) as a **Web Service**
2. Add your `client_secrets.json` file for Google API
3. Use the URL in your Google Apps Script to trigger conversion

## Requirements

- ffmpeg must be available in the environment (Render should support this with proper build config)
