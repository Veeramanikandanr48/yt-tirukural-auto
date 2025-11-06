"""
Configuration file for video generation and YouTube upload settings
All settings can be modified here for easy customization
"""
import os
from datetime import date

# ============================================================================
# FILE PATHS
# ============================================================================
IMAGE_PATH = "assets/bg/Gemini_Generated_Image_fcl59hfcl59hfcl5.png"
FONT_PATH = "assets/fonts/Lohit-Tamil.ttf"  # Reliable Tamil font - verified to work
TEXT_COLOR = (0, 0, 0)  # Pure black text color (RGB)
TEXT_STROKE_WIDTH_MULTIPLIER = 4  # Multiplier for stroke width to make text bolder (higher = bolder)
TEXT_STROKE_COLOR = (255, 255, 255)  # White stroke for contrast (RGB)
OUTPUT_DIR = "dist"
AUDIO_DIR = "data/audio_generated"
TEMP_DIR = "temp"
LOG_DIR = "logs"

# ============================================================================
# VIDEO SETTINGS
# ============================================================================
FONT_SIZE = 30  # Base font size (will be scaled for 4K)
MIN_VIDEO_DURATION = 30.0  # Minimum video duration in seconds

# 4K YouTube Shorts Video Quality Settings (Vertical 9:16 format)
VIDEO_RESOLUTION = (2160, 3840)  # 4K UHD YouTube Shorts resolution (width, height) - Vertical 9:16 aspect ratio
VIDEO_FPS = 30  # Frames per second (30fps for smooth playback)
VIDEO_BITRATE = "35000k"  # Video bitrate (35Mbps for 4K high quality - YouTube recommends 35-45Mbps for 4K)
VIDEO_CODEC = "libx264"  # H.264 codec (best compatibility)
VIDEO_PRESET = "slow"  # Encoding preset (slower = better quality): ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
AUDIO_BITRATE = "256k"  # Audio bitrate (256kbps for high quality 4K)
AUDIO_CODEC = "aac"  # Audio codec

# ============================================================================
# AUDIO/BGM SETTINGS
# ============================================================================
BGM_PATH = "assets/music/Hovering Thoughts - Spence.mp3"  # Set to None to disable BGM
BGM_VOLUME = 0.3  # BGM volume (0.0 to 1.0)

# ============================================================================
# YOUTUBE UPLOAD CONFIGURATION
# ============================================================================
YOUTUBE_UPLOAD_ENABLED = True  # Set to True to enable automatic uploads
YOUTUBE_CHANNEL_NAME = "Wisdom Connect Global"  # Your YouTube channel name
YOUTUBE_CLIENT_SECRETS_FILE = "client_secrets.json"  # OAuth2 client secrets file
YOUTUBE_TOKEN_FILE = "token.pickle"  # Token file to store credentials
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
YOUTUBE_PRIVACY_STATUS = "private"  # Options: "private", "unlisted", "public"
YOUTUBE_CATEGORY_ID = "27"  # Category ID (27 = Education)
YOUTUBE_DEFAULT_LANGUAGE = "ta"  # Default language code (ta = Tamil)
YOUTUBE_DEFAULT_AUDIO_LANGUAGE = "ta"  # Default audio language code

# ============================================================================
# SCHEDULING CONFIGURATION
# ============================================================================
YOUTUBE_SCHEDULE_ENABLED = True  # Set to True to schedule videos
YOUTUBE_SCHEDULE_TIME = "15:00"  # Schedule time in 24-hour format (HH:MM)
YOUTUBE_SCHEDULE_START_DATE = date.today().strftime("%Y-%m-%d")  # Start date (YYYY-MM-DD)
YOUTUBE_TIMEZONE = "Asia/Kolkata"  # Timezone for scheduling

# ============================================================================
# TTS MODEL CONFIGURATION
# ============================================================================
TTS_MODEL_NAME = "facebook/mms-tts-tam"  # TTS model name
TTS_DEVICE = "cpu"  # Device to use: "cpu" or "cuda"

# ============================================================================
# INITIALIZE DIRECTORIES
# ============================================================================
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

