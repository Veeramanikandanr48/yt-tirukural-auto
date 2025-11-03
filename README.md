# Thirukural Video Generator

Automated video generation system for creating educational Thirukural videos with Tamil text, audio narration, and YouTube upload capability.

## Features

- 🤖 **Automated Video Generation**: Generate videos from Thirukural verses with background music
- 🎙️ **TTS Audio**: Text-to-speech generation using Tamil TTS models
- 📝 **Tamil Text Rendering**: Proper Tamil font rendering with adhigaram (chapter) names
- 🎬 **Video Composition**: Combine images, text overlays, and audio into MP4 videos
- 📺 **YouTube Integration**: Automatic upload and scheduling to YouTube
- ⚙️ **Configurable**: Easy configuration through `config.py`

## Project Structure

```
yt-tirukural-auto/
├── assets/
│   ├── fonts/          # Tamil fonts
│   ├── bg/             # Background images
│   └── music/           # Background music files
├── data/
│   └── audio_generated/ # Generated audio files
├── dist/                # Output video files
├── temp/                # Temporary files
├── logs/                # Log files
├── config.py            # Configuration file
├── generate_batch_videos.py  # Main script
└── requirements.txt     # Python dependencies
```

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure**:
   - Edit `config.py` to set paths, font size, BGM settings, etc.
   - For YouTube upload, see `YOUTUBE_SETUP.md`

3. **Add Assets**:
   - Place background image in `assets/bg/`
   - Place Tamil font in `assets/fonts/`
   - (Optional) Place background music in `assets/music/`

4. **Run**:
   ```bash
   python generate_batch_videos.py
   ```

## Configuration

Key settings in `config.py`:
- `IMAGE_PATH`: Background image path
- `FONT_PATH`: Tamil font path
- `BGM_PATH`: Background music path (or None to disable)
- `YOUTUBE_UPLOAD_ENABLED`: Enable/disable YouTube upload
- `YOUTUBE_SCHEDULE_ENABLED`: Enable video scheduling

## YouTube Integration

See `YOUTUBE_SETUP.md` for detailed YouTube API setup instructions.

## Requirements

- Python 3.10+
- See `requirements.txt` for full dependency list

## License

[Add your license here]

