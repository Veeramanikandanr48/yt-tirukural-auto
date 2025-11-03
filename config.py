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
FONT_PATH = "assets/fonts/VANAVIL-Avvaiyar Regular.otf"
OUTPUT_DIR = "dist"
AUDIO_DIR = "data/audio_generated"
TEMP_DIR = "temp"
LOG_DIR = "logs"

# ============================================================================
# VIDEO SETTINGS
# ============================================================================
FONT_SIZE = 24
MIN_VIDEO_DURATION = 30.0  # Minimum video duration in seconds

# ============================================================================
# AUDIO/BGM SETTINGS
# ============================================================================
BGM_PATH = "assets/music/Hovering Thoughts - Spence.mp3"  # Set to None to disable BGM
BGM_VOLUME = 0.3  # BGM volume (0.0 to 1.0)

# ============================================================================
# YOUTUBE UPLOAD CONFIGURATION
# ============================================================================
YOUTUBE_UPLOAD_ENABLED = False  # Set to True to enable automatic uploads
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
YOUTUBE_SCHEDULE_TIME = "08:00"  # Schedule time in 24-hour format (HH:MM)
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

