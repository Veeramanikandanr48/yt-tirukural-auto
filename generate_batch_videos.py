from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.audio.AudioClip import CompositeAudioClip, AudioArrayClip
# volumex import - try different paths for different moviepy versions
volumex = None
try:
    from moviepy.audio.fx.volumex import volumex
except ImportError:
    try:
        from moviepy.video.fx.volumex import volumex
    except ImportError:
        try:
            # For moviepy 2.0+, try video.fx.all
            from moviepy.video.fx.all import volumex
        except ImportError:
            # Create a simple volumex function if not available
            def volumex(clip, factor):
                """Volume multiplier - fallback implementation"""
                # Try different methods based on moviepy version
                if hasattr(clip, 'volumex'):
                    return clip.volumex(factor)
                elif hasattr(clip, 'with_volume'):
                    return clip.with_volume(factor)
                elif hasattr(clip, 'set_volume'):
                    return clip.set_volume(factor)
                else:
                    # Last resort: return clip unchanged
                    return clip
from PIL import Image, ImageDraw, ImageFont
from transformers import VitsModel, AutoTokenizer
import torch
import scipy.io.wavfile as wavfile
import os

import numpy as np
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import pickle
from datetime import datetime, timedelta, date
import json
import random
import glob
import config
from youtube_mcp import get_mcp_integration

# Configuration - Import from config.py
# Convert relative paths to absolute paths to ensure they work from any directory
# Background image folder path
bg_folder_path = os.path.abspath("assets/bg")
font_path = os.path.abspath(config.FONT_PATH)
font_size = config.FONT_SIZE
output_dir = os.path.abspath(config.OUTPUT_DIR)
audio_dir = os.path.abspath(config.AUDIO_DIR)
bgm_path = os.path.abspath(config.BGM_PATH) if config.BGM_PATH else None
bgm_volume = config.BGM_VOLUME

# YouTube Upload Configuration - Import from config.py
YOUTUBE_UPLOAD_ENABLED = config.YOUTUBE_UPLOAD_ENABLED
YOUTUBE_CHANNEL_NAME = config.YOUTUBE_CHANNEL_NAME
YOUTUBE_CLIENT_SECRETS_FILE = config.YOUTUBE_CLIENT_SECRETS_FILE
YOUTUBE_TOKEN_FILE = config.YOUTUBE_TOKEN_FILE
YOUTUBE_SCOPES = config.YOUTUBE_SCOPES
YOUTUBE_PRIVACY_STATUS = config.YOUTUBE_PRIVACY_STATUS

# Scheduling Configuration - Import from config.py
YOUTUBE_SCHEDULE_ENABLED = config.YOUTUBE_SCHEDULE_ENABLED
YOUTUBE_SCHEDULE_TIMES = config.YOUTUBE_SCHEDULE_TIMES  # List of schedule times
YOUTUBE_SCHEDULE_START_DATE = config.YOUTUBE_SCHEDULE_START_DATE
YOUTUBE_TIMEZONE = config.YOUTUBE_TIMEZONE


# Load Thirukural data from JSON file
def load_thirukural_data(json_path="thirukural_git.json"):
    """Load Thirukural data from JSON file"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✓ Loaded {len(data['kurals'])} kurals from {json_path}")
        return data
    except FileNotFoundError:
        print(f"⚠ Warning: {json_path} not found. Using empty data.")
        return {"kurals": [], "chapters": []}
    except Exception as e:
        print(f"⚠ Error loading {json_path}: {e}. Using empty data.")
        return {"kurals": [], "chapters": []}

# Load the data
thirukural_data = load_thirukural_data()

# Extract kurals data - combine line1 and line2 into full verse
sentences = []
meanings = []
english_translations = []  # Store English translations
kural_chapters = {}  # Store chapter name for each kural number

for kural in thirukural_data.get('kurals', []):
    kural_num = kural.get('number', 0)
    if kural_num > 0:
        # Combine the two lines into one sentence
        line1 = kural.get('kural', [''])[0] if kural.get('kural') else ''
        line2 = kural.get('kural', [''])[1] if len(kural.get('kural', [])) > 1 else ''
        full_verse = f"{line1} {line2}".strip()
        sentences.append(full_verse)
        
        # Extract meaning - only ta_mu_va meaning (without name prefix)
        meaning_obj = kural.get('meaning', {})
        
        # Use only ta_mu_va meaning without the name prefix
        if meaning_obj.get('ta_mu_va'):
            meanings.append(meaning_obj['ta_mu_va'])
        else:
            meanings.append("")
        
        # Extract English translation
        english_translations.append(meaning_obj.get('en', ''))
        
        # Store chapter name for this kural
        chapter_name = kural.get('chapter', '')
        if chapter_name:
            kural_chapters[kural_num] = chapter_name

# Function to get adhigaram name for a kural number
def get_adhigaram_name(kural_number):
    """Get the adhigaram (chapter) name for a given kural number (1-based)"""
    return kural_chapters.get(kural_number, "")

# Initialize TTS model
print("Loading TTS model...")
model_name = config.TTS_MODEL_NAME
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = VitsModel.from_pretrained(model_name).to(config.TTS_DEVICE)
print("✓ TTS model loaded")


# Function to get athirakaram (first word) from Thirukural
def get_athirakaram(text):
    """Extract the first word (athirakaram) from Thirukural verse"""
    # Remove period if present
    text = text.rstrip('.')
    words = text.split()
    if words:
        return words[0]  # Return first word
    return ""

# Function to split Tirukural into 4 words + 3 words
def split_tirukural(text):
    """Split Tirukural verse into two lines: first 4 words, then remaining words
    Properly handles Tamil text by preserving word boundaries and character order"""
    # Remove period if present
    text = text.rstrip('.').strip()
    
    # Split by spaces - Tamil uses spaces between words
    words = text.split()
    
    # Filter out empty strings
    words = [w for w in words if w.strip()]
    
    if len(words) >= 7:
        # First 4 words for line 1, remaining for line 2
        line1 = ' '.join(words[:4])
        line2 = ' '.join(words[4:])
    elif len(words) > 0:
        # If less than 7 words, split roughly in half
        mid = (len(words) + 1) // 2  # Add 1 to ensure second line gets any extra word
        line1 = ' '.join(words[:mid])
        line2 = ' '.join(words[mid:])
    else:
        # Fallback if no words
        line1 = text[:len(text)//2] if text else ""
        line2 = text[len(text)//2:] if text else ""
    
    # Ensure no leading/trailing spaces
    line1 = line1.strip()
    line2 = line2.strip()
    
    return line1, line2

# Function to format Tamil text with proper punctuation for better pronunciation
def format_tamil_text_for_tts(text):
    """Format Tamil text with proper punctuation and pauses for clear TTS pronunciation and rhythmic delivery"""
    if not text:
        return text
    
    # Replace multiple spaces with single space first
    text = ' '.join(text.split())
    
    # Add proper spacing around punctuation for better pronunciation
    # Multiple periods create longer pauses (for 7 swaram style rhythm)
    # First, handle multiple periods (they should create longer pauses)
    text = text.replace('...', ' . . . ')  # Three periods = longer pause
    text = text.replace('..', ' . . ')      # Two periods = medium pause
    text = text.replace('.', ' . ')         # Single period = short pause
    
    # Add spacing for other punctuation
    text = text.replace(',', ' , ')
    text = text.replace('?', ' ? ')
    text = text.replace('!', ' ! ')
    text = text.replace(':', ' : ')
    text = text.replace(';', ' ; ')
    
    # Clean up multiple spaces but preserve intentional spacing for pauses
    # Split and rejoin to normalize spaces
    words = text.split()
    text = ' '.join(words)
    
    return text

# Function to slow down audio for better clarity
def slow_down_audio(audio_data, sample_rate, speed_factor=1.1):    
    """
    Slow down audio by time-stretching using simple resampling
    speed_factor < 1.0 makes it slower, > 1.0 makes it faster
    """
    # Use linear interpolation to slow down audio
    original_length = len(audio_data)
    new_length = int(original_length / speed_factor)
    
    # Create indices for interpolation
    indices = np.linspace(0, original_length - 1, new_length)
    
    # Linear interpolation
    slowed_audio = np.interp(indices, np.arange(original_length), audio_data)
    
    return slowed_audio.astype(np.float32)

# Function to create silence (delay) in audio
def insert_silence(audio_data, sample_rate, duration_seconds=1.0):
    """
    Insert silence (delay) into audio
    duration_seconds: duration of silence in seconds
    """
    silence_samples = int(sample_rate * duration_seconds)
    silence = np.zeros(silence_samples, dtype=np.float32)
    return silence

# Function to concatenate audio segments with delays
def concatenate_audio_with_delays(segments, sample_rate, delay_between=1.0):
    """
    Concatenate multiple audio segments with silence delays between them
    segments: list of audio arrays
    sample_rate: sample rate of audio
    delay_between: delay in seconds between segments
    """
    if not segments:
        return np.array([], dtype=np.float32)
    
    # Create delay (silence)
    delay = insert_silence(segments[0], sample_rate, delay_between)
    
    # Start with first segment
    result = segments[0].copy()
    
    # Add delay and subsequent segments
    for segment in segments[1:]:
        result = np.concatenate([result, delay, segment])
    
    return result

# Function to generate audio from text with emotion
def generate_audio(text, output_path, meaning=""):
    """Generate audio file from Tamil text using TTS with proper punctuation, delays, and rhythmic delivery (7 swaram style)"""
    channel_name = YOUTUBE_CHANNEL_NAME
    ending_message = f"இது போன்ற தகவல்களை நீங்கள் அறிய விரும்பினால் நம் {channel_name} சேனலை சப்ஸ்கிரைப் செய்யுங்கள்"
    
    print(f"\nGenerating audio for: {text}")
    
    sample_rate = model.config.sampling_rate
    audio_segments = []
    
    # Generate each section separately for proper delays
    # Section 1: Kural text
    kural_text = format_tamil_text_for_tts(text)
    inputs = tokenizer(kural_text, return_tensors="pt")
    with torch.no_grad():
        output = model(**inputs).waveform
    kural_audio = output.cpu().numpy()[0].astype(np.float32)
    # Normalize
    max_val = np.max(np.abs(kural_audio))
    if max_val > 0:
        kural_audio = kural_audio / max_val
    # Slow down (increased speed for faster delivery)
    kural_audio = slow_down_audio(kural_audio, sample_rate, speed_factor=1.1)
    audio_segments.append(kural_audio)
    
    if meaning:
        # Section 2: "இதன் பொருள்"
        porul_text = format_tamil_text_for_tts("இதன் பொருள்")
        inputs = tokenizer(porul_text, return_tensors="pt")
        with torch.no_grad():
            output = model(**inputs).waveform
        porul_audio = output.cpu().numpy()[0].astype(np.float32)
        max_val = np.max(np.abs(porul_audio))
        if max_val > 0:
            porul_audio = porul_audio / max_val
        porul_audio = slow_down_audio(porul_audio, sample_rate, speed_factor=1.1)
        audio_segments.append(porul_audio)
        
        # Section 3: Meaning
        meaning_text = format_tamil_text_for_tts(meaning)
        inputs = tokenizer(meaning_text, return_tensors="pt")
        with torch.no_grad():
            output = model(**inputs).waveform
        meaning_audio = output.cpu().numpy()[0].astype(np.float32)
        max_val = np.max(np.abs(meaning_audio))
        if max_val > 0:
            meaning_audio = meaning_audio / max_val
        meaning_audio = slow_down_audio(meaning_audio, sample_rate, speed_factor=1.1)
        audio_segments.append(meaning_audio)
        print(f"Including meaning: {meaning[:50]}...")
    
    # Section 4: Ending message
    ending_text = format_tamil_text_for_tts(ending_message)
    inputs = tokenizer(ending_text, return_tensors="pt")
    with torch.no_grad():
        output = model(**inputs).waveform
    ending_audio = output.cpu().numpy()[0].astype(np.float32)
    max_val = np.max(np.abs(ending_audio))
    if max_val > 0:
        ending_audio = ending_audio / max_val
    ending_audio = slow_down_audio(ending_audio, sample_rate, speed_factor=1.1)
    audio_segments.append(ending_audio)
    
    # Combine all segments with proper delays (reduced delay for faster flow)
    delay_seconds = 0.4  # 0.8 second delay between sections
    audio_data = concatenate_audio_with_delays(audio_segments, sample_rate, delay_between=delay_seconds)
    print(f"  ✓ Added {delay_seconds}s delays between sections")
    
    # Apply slight pitch variation and emphasis for emotional expression
    # Create a smooth envelope for emphasis
    length = len(audio_data)
    envelope = np.ones(length)
    
    # Add emphasis at key points (verse end, meaning transitions)
    # More gradual emphasis for better pronunciation
    emphasis_points = [int(length * 0.3), int(length * 0.6), int(length * 0.85)]
    for point in emphasis_points:
        window = int(length * 0.08)  # Smaller window for smoother transitions
        start = max(0, point - window)
        end = min(length, point + window)
        envelope[start:end] = np.linspace(1.0, 1.12, end - start)  # Less aggressive emphasis
    
    # Apply envelope
    audio_data = audio_data * envelope
    
    # Normalize again
    max_val = np.max(np.abs(audio_data))
    if max_val > 0:
        audio_data = audio_data / max_val
    
    # Convert back to int16 for wavfile
    audio_int16 = (audio_data * 32767).astype(np.int16)
    
    wavfile.write(output_path, sample_rate, audio_int16)
    print(f"✓ Audio saved: {output_path}")
    return output_path

# Global font cache (per size)
_font_cache = {}

# Function to reset font cache
def reset_font_cache():
    """Reset the font cache to force reload"""
    global _font_cache
    _font_cache = {}

# Function to load Tamil font
def load_tamil_font(size, verbose=False):
    """Load Tamil font with fallbacks (cached per size)"""
    global _font_cache
    # Check cache for this size
    if size in _font_cache:
        return _font_cache[size]
    
    font = None
    
    # PRIORITY 1: Try custom font from config first (most reliable)
    try:
        # Use absolute path to ensure it works from any directory
        abs_font_path = os.path.abspath(font_path)
        if os.path.exists(abs_font_path):
            font = ImageFont.truetype(abs_font_path, size)
            if verbose:
                print(f"✓ Loaded custom font: {os.path.basename(abs_font_path)} (size {size})")
                print(f"  Full path: {abs_font_path}")
            _font_cache[size] = font
            return font
        elif verbose:
            print(f"⚠ Font file not found: {abs_font_path}")
    except Exception as e:
        if verbose:
            print(f"⚠ Could not load custom font: {e}")
            import traceback
            traceback.print_exc()
    
    # PRIORITY 2: Try Linux system Tamil fonts
    linux_tamil_fonts = [
        "/usr/share/fonts/truetype/lohit-tamil/Lohit-Tamil.ttf",
        "/usr/share/fonts/truetype/lohit-tamil-classical/Lohit-Tamil-Classical.ttf",
        "/usr/share/fonts/truetype/samyak-fonts/Samyak-Tamil.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
        "/usr/share/fonts/TTF/NotoSansTamil-Regular.ttf",
        "/usr/share/fonts/TTF/NotoSansTamil-Bold.ttf",
    ]
    
    for linux_font in linux_tamil_fonts:
        try:
            if os.path.exists(linux_font):
                font = ImageFont.truetype(linux_font, size)
                if verbose:
                    print(f"✓ Loaded Linux system font: {os.path.basename(linux_font)} (size {size})")
                _font_cache[size] = font
                return font
        except Exception as e:
            if verbose:
                print(f"⚠ Could not load {linux_font}: {e}")
            continue
    
    # PRIORITY 3: Try Windows Tamil fonts (for Windows users)
    windows_tamil_fonts = [
        "C:/Windows/Fonts/muktamalar.ttf",
        "C:/Windows/Fonts/NotoSansTamil-Regular.ttf",
        "C:/Windows/Fonts/NotoSansTamil-Bold.ttf",
        "C:/Windows/Fonts/catamaran.ttf",
        "C:/Windows/Fonts/Pothana2000.ttf",
        "C:/Windows/Fonts/Vani.ttf",
        "C:/Windows/Fonts/nirmala.ttf",
        "C:/Windows/Fonts/nirmalab.ttf",
        "C:/Windows/Fonts/latha.ttf",
        "C:/Windows/Fonts/gautami.ttf",
    ]
    
    for win_font in windows_tamil_fonts:
        try:
            if os.path.exists(win_font):
                font = ImageFont.truetype(win_font, size)
                if verbose:
                    print(f"✓ Loaded Windows font: {os.path.basename(win_font)} (size {size})")
                _font_cache[size] = font
                return font
        except:
            continue
    
    # Fallback to default (will show boxes for Tamil characters)
    if verbose:
        print("⚠ Warning: No Tamil font found! Using default font (Tamil text may show as boxes)")
    font = ImageFont.load_default()
    _font_cache[size] = font
    return font

# Function to get all background images from the bg folder
def get_background_images():
    """Get all image files from the background folder"""
    image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.PNG', '*.JPG', '*.JPEG']
    bg_images = []
    for ext in image_extensions:
        bg_images.extend(glob.glob(os.path.join(bg_folder_path, ext)))
    return bg_images

# Function to randomly select a background image
def get_random_background():
    """Randomly select a background image from the bg folder"""
    bg_images = get_background_images()
    if not bg_images:
        raise FileNotFoundError(f"No background images found in {bg_folder_path}")
    selected_image = random.choice(bg_images)
    print(f"  🎨 Selected background: {os.path.basename(selected_image)}")
    return selected_image

# Function to create video from text and audio

def create_video(text, audio_path, output_video_path, kural_number=1):
    """Create video with text overlay and audio"""
    print(f"\nCreating video: {output_video_path}")
    
    # Load audio
    audio_clip = AudioFileClip(audio_path)
    
    # Randomly select a background image
    image_path = get_random_background()
    
    # Open background image and resize to 4K resolution
    img = Image.open(image_path).convert("RGBA")
    
    # Get 4K resolution from config (width, height)
    target_width, target_height = config.VIDEO_RESOLUTION
    
    # Resize image to 4K while maintaining aspect ratio, then crop to exact 4K
    img_aspect = img.width / img.height
    target_aspect = target_width / target_height
    
    if img_aspect > target_aspect:
        # Image is wider - fit to height, crop width
        new_height = target_height
        new_width = int(img.width * (target_height / img.height))
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        # Crop to exact width
        left = (new_width - target_width) // 2
        img = img.crop((left, 0, left + target_width, target_height))
    else:
        # Image is taller - fit to width, crop height
        new_width = target_width
        new_height = int(img.height * (target_width / img.width))
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        # Crop to exact height
        top = (new_height - target_height) // 2
        img = img.crop((0, top, target_width, top + target_height))
    
    print(f"  ✓ Image resized to 4K: {img.size[0]}x{img.size[1]}")
    draw = ImageDraw.Draw(img)
    
    # Scale font size for 4K (proportional to 1080p baseline)
    # If config font_size is for 1080p, scale for 2160p (4K)
    scale_factor = target_height / 1080  # Assuming base resolution was 1080p
    scaled_font_size = int(font_size * scale_factor)
    scaled_adhigaram_font_size = int((font_size + 4) * scale_factor)
    
    # Load font (from cache) with scaled size for 4K
    font = load_tamil_font(scaled_font_size, verbose=True)
    # Verify font is actually loaded (not None)
    if font is None:
        print("  ⚠ ERROR: Font is None! This will cause boxes.")
        font = ImageFont.load_default()
    else:
        # Check if it's the default font (which shows boxes)
        if hasattr(font, 'path'):
            print(f"  ✓ Using font: {font.path}")
        else:
            print(f"  ✓ Font loaded (type: {type(font).__name__})")
    
    # Debug: Test font with a simple Tamil character
    try:
        test_img = Image.new('RGBA', (100, 50), (255, 255, 255, 0))
        test_draw = ImageDraw.Draw(test_img)
        test_text = "வ"
        bbox_test = test_draw.textbbox((0, 0), test_text, font=font)
        print(f"  ✓ Font test: Tamil character 'வ' renders with bbox: {bbox_test}")
    except Exception as e:
        print(f"  ⚠ Font test failed: {e}")

    # Get adhigaram name for this kural
    adhigaram = get_adhigaram_name(kural_number)
    
    # Ensure text is properly encoded as UTF-8 string
    if isinstance(text, bytes):
        text = text.decode('utf-8')
    if isinstance(adhigaram, bytes):
        adhigaram = adhigaram.decode('utf-8')
    
    # Split text into two lines (4 words + 3 words)
    line1, line2 = split_tirukural(text)
    
    # Debug: Print text to verify it's correct
    print(f"  Text to render: {text}")
    print(f"  Line 1: {line1}")
    print(f"  Line 2: {line2}")
    if adhigaram:
        print(f"  Adhigaram: {adhigaram}")
    
    # Calculate positions for adhigaram at top (scaled for 4K)
    top_margin = int(50 * scale_factor)  # Margin from top (scaled for 4K)
    if adhigaram:
        adhigaram_font = load_tamil_font(scaled_adhigaram_font_size, verbose=True)
        # Verify adhigaram font is loaded
        if adhigaram_font is None:
            print("  ⚠ ERROR: Adhigaram font is None! Using regular font.")
            adhigaram_font = font
        # Use textbbox with explicit direction and language for accurate Tamil measurement
        try:
            # Try with language and direction parameters (Pillow 8.0+)
            bbox_adhigaram = draw.textbbox((0, 0), adhigaram, font=adhigaram_font, direction="ltr", language="ta")
            use_language_params_adhigaram = True
        except (TypeError, KeyError):
            # Fallback for older Pillow versions or when libraqm is not available
            bbox_adhigaram = draw.textbbox((0, 0), adhigaram, font=adhigaram_font)
            use_language_params_adhigaram = False
        
        adhigaram_width = bbox_adhigaram[2] - bbox_adhigaram[0]
        adhigaram_height = bbox_adhigaram[3] - bbox_adhigaram[1]
        adhigaram_x = (img.width - adhigaram_width) // 2  # Center horizontally
        adhigaram_y = top_margin
        
        # Add padding for white background box (scaled for 4K)
        padding_x = int(20 * scale_factor)  # Horizontal padding
        padding_y = int(10 * scale_factor)  # Vertical padding
        
        # Draw white background rectangle
        bg_x1 = adhigaram_x - padding_x
        bg_y1 = adhigaram_y - padding_y
        bg_x2 = adhigaram_x + adhigaram_width + padding_x
        bg_y2 = adhigaram_y + adhigaram_height + padding_y
        draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill="white")
        
        # Draw adhigaram text on white background - black text
        # Explicitly set direction and language for proper Tamil rendering (if supported)
        if use_language_params_adhigaram:
            draw.text((adhigaram_x, adhigaram_y), adhigaram, font=adhigaram_font, fill="black", direction="ltr", language="ta")
        else:
            # Fallback for older Pillow versions
            draw.text((adhigaram_x, adhigaram_y), adhigaram, font=adhigaram_font, fill="black")
    
    # Calculate positions for both lines (verse text)
    # Use textbbox for accurate measurement of Tamil text with proper language support
    try:
        # Try with language and direction parameters (Pillow 8.0+)
        bbox1 = draw.textbbox((0, 0), line1, font=font, direction="ltr", language="ta")
        bbox2 = draw.textbbox((0, 0), line2, font=font, direction="ltr", language="ta")
        use_language_params = True
    except (TypeError, KeyError):
        # Fallback for older Pillow versions or when libraqm is not available
        bbox1 = draw.textbbox((0, 0), line1, font=font)
        bbox2 = draw.textbbox((0, 0), line2, font=font)
        use_language_params = False
    
    text_width1 = bbox1[2] - bbox1[0]
    text_width2 = bbox2[2] - bbox2[0]
    text_height1 = bbox1[3] - bbox1[1]
    text_height2 = bbox2[3] - bbox2[1]
    
    # Calculate vertical spacing - zero spacing for tightest box
    line_spacing = 0  # No spacing between lines
    
    # Left-align both lines with margin from left edge (scaled for 4K)
    left_margin = int(50 * scale_factor)  # Margin from left (scaled for 4K)
    x1 = left_margin
    x2 = left_margin
    
    # Position higher up from bottom (scaled for 4K)
    bottom_margin = int(100 * scale_factor)  # Margin from bottom (scaled for 4K)
    y2 = img.height - text_height2 - bottom_margin  # Second line
    y1 = y2 - text_height1 - line_spacing  # First line (above)
    
    verse_padding_x = int(40 * scale_factor)  # Horizontal padding (increased from 20)
    verse_padding_y = int(25 * scale_factor)  # Vertical padding (added for more space)
    bbox_crop_factor = 0.15  # Reduced crop factor from 0.4 to 0.15 for larger background
    
    verse_bg_x1 = x1 - verse_padding_x
    # Crop less aggressively from top to increase height
    bbox1_top = y1 + bbox1[1] + int((bbox1[3] - bbox1[1]) * bbox_crop_factor)
    bbox2_top = y2 + bbox2[1] + int((bbox2[3] - bbox2[1]) * bbox_crop_factor)
    verse_bg_y1 = min(bbox1_top, bbox2_top) - verse_padding_y
    
    verse_bg_x2 = max(x1 + text_width1, x2 + text_width2) + verse_padding_x
    # Crop less aggressively from bottom to increase height
    bbox1_bottom = y1 + bbox1[3] - int((bbox1[3] - bbox1[1]) * bbox_crop_factor)
    bbox2_bottom = y2 + bbox2[3] - int((bbox2[3] - bbox2[1]) * bbox_crop_factor)
    verse_bg_y2 = max(bbox1_bottom, bbox2_bottom) + verse_padding_y
    
    # Draw white background rectangle for verse text
    draw.rectangle([verse_bg_x1, verse_bg_y1, verse_bg_x2, verse_bg_y2], fill="white")
    
    # Draw both lines - black text (no stroke needed with white background)
    print(f"  Drawing line1 at ({x1}, {y1}): {line1[:30]}...")
    print(f"  Drawing line2 at ({x2}, {y2}): {line2[:30]}...")
    try:
        if use_language_params:
            draw.text((x1, y1), line1, font=font, fill="black", direction="ltr", language="ta")
            draw.text((x2, y2), line2, font=font, fill="black", direction="ltr", language="ta")
        else:
            # Fallback for older Pillow versions
            draw.text((x1, y1), line1, font=font, fill="black")
            draw.text((x2, y2), line2, font=font, fill="black")
        print(f"  ✓ Text drawn successfully")
    except Exception as e:
        print(f"  ⚠ ERROR drawing text: {e}")
        import traceback
        traceback.print_exc()
    
    # Save temporary image
    temp_image_path = os.path.join(config.TEMP_DIR, "text_image.png")
    
    # Convert RGBA to RGB if needed for video compatibility
    # But preserve the original appearance
    final_img = img
    if img.mode == 'RGBA':
        # For video, we need RGB, but we want to preserve transparency properly
        # Create RGB version by compositing on white background for video
        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
        rgb_img.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
        final_img = rgb_img
    elif img.mode != 'RGB':
        final_img = img.convert('RGB')
    
    final_img.save(temp_image_path)
    print(f"  ✓ Saved temporary image: {temp_image_path}")
    print(f"  Image mode: {final_img.mode}, size: {final_img.size}")
    
    # Debug: Also save a copy with kural number for inspection
    debug_image_path = os.path.join(config.TEMP_DIR, f"debug_text_{kural_number:03d}.png")
    final_img.save(debug_image_path)
    print(f"  ✓ Saved debug image: {debug_image_path}")
    

    # Create video - let audio complete fully, extend with silence if needed to reach minimum 30 seconds
    min_duration = config.MIN_VIDEO_DURATION
    audio_duration = audio_clip.duration
    
    # Process main audio - complete sentence fully, extend if shorter than 30 seconds
    silence_clip = None
    extended_audio = None
    if audio_duration < min_duration:
        # Extend audio with silence to reach minimum 30 seconds
        silence_duration = min_duration - audio_duration
        # Create silent audio clip matching the audio format
        sampling_rate = int(audio_clip.fps)
        channels = 2 if audio_clip.nchannels == 2 else 1
        silent_samples = int(silence_duration * sampling_rate)
        if channels == 2:
            silent_array = np.zeros((silent_samples, 2), dtype=np.float32)
        else:
            silent_array = np.zeros(silent_samples, dtype=np.float32)
        silence_clip = AudioArrayClip(silent_array, fps=sampling_rate)
        # Use set_start for moviepy 1.0.3
        silence_with_start = silence_clip.set_start(audio_duration)
        extended_audio = CompositeAudioClip([audio_clip, silence_with_start])
        main_audio = extended_audio
        target_duration = min_duration  # Use minimum duration (30 seconds)
    else:
        # Audio is 30 seconds or longer - use full audio duration (complete sentence)
        main_audio = audio_clip
        target_duration = audio_duration  # Use actual audio duration (may be longer than 30 seconds)
    
    # Add BGM if configured
    bgm_clip = None
    bgm_looped = None
    if bgm_path and os.path.exists(bgm_path):
        try:
            print(f"  Adding BGM: {bgm_path}")
            bgm_clip = AudioFileClip(bgm_path)
            # Loop BGM to match target duration (full audio duration)
            bgm_duration = bgm_clip.duration
            if bgm_duration < target_duration:
                # Loop BGM manually by repeating it
                num_loops = int(target_duration / bgm_duration) + 1
                bgm_looped = CompositeAudioClip([bgm_clip] * num_loops).subclip(0, target_duration)
            else:
                # Use full BGM if it's longer, or trim to match target duration
                bgm_looped = bgm_clip.subclip(0, target_duration)
            
            # Lower BGM volume
            # Use volumex if available, otherwise use with_volume or set_volume
            try:
                bgm_looped = bgm_looped.fx(volumex, bgm_volume)
            except (AttributeError, TypeError):
                # Fallback for newer moviepy versions
                if hasattr(bgm_looped, 'with_volume'):
                    bgm_looped = bgm_looped.with_volume(bgm_volume)
                elif hasattr(bgm_looped, 'set_volume'):
                    bgm_looped = bgm_looped.set_volume(bgm_volume)
                elif hasattr(bgm_looped, 'volumex'):
                    bgm_looped = bgm_looped.volumex(bgm_volume)
                else:
                    # If no volume method available, skip volume adjustment
                    print(f"  ⚠ Warning: Could not adjust BGM volume, using original volume")
            
            # Mix TTS audio with BGM
            final_audio = CompositeAudioClip([bgm_looped, main_audio])
            
        except Exception as e:
            print(f"  ⚠ Warning: Could not add BGM: {e}")
            final_audio = main_audio
            if bgm_clip:
                bgm_clip.close()
            bgm_clip = None
            bgm_looped = None
    else:
        final_audio = main_audio
    
    # Create image clip to match full audio duration (complete sentence)
    # Use the saved temporary image (already converted to RGB if needed)
    image_clip = ImageSequenceClip([temp_image_path], durations=[target_duration])
    video = image_clip.set_audio(final_audio)
    
    # Write video with 4K quality settings from config
    video.write_videofile(
        output_video_path,
        fps=config.VIDEO_FPS,
        bitrate=config.VIDEO_BITRATE,
        codec=config.VIDEO_CODEC,
        preset=config.VIDEO_PRESET,
        audio_bitrate=config.AUDIO_BITRATE,
        audio_codec=config.AUDIO_CODEC,
        verbose=False,
        logger=None
    )
    
    # Cleanup - close clips to free resources

    # Note: Close in order and avoid comparing clips (can cause errors if already closed)
    try:
        video.close()
    except:
        pass
    
    try:
        image_clip.close()
    except:
        pass
    
    # Close final_audio if it's a CompositeAudioClip (it contains other clips)
    try:
        if isinstance(final_audio, CompositeAudioClip):
            final_audio.close()
    except:
        pass
    
    # Close extended audio if it exists (it's also a composite)
    if extended_audio is not None:
        try:
            extended_audio.close()
        except:
            pass
    
    # Close silence clip if it exists
    if silence_clip is not None:
        try:
            silence_clip.close()
        except:
            pass
    
    # Close BGM clips
    if bgm_looped is not None:
        try:
            bgm_looped.close()
        except:
            pass
    if bgm_clip is not None:
        try:
            bgm_clip.close()
        except:
            pass
    
    # Close main audio clip last (it may have been used in composites)
    try:
        audio_clip.close()
    except:
        pass
    
    if os.path.exists(temp_image_path):
        os.remove(temp_image_path)
    
    print(f"✓ Video created: {output_video_path}")
    return output_video_path


# YouTube Upload Functions
def get_authenticated_service():
    """Authenticate and return YouTube service"""
    creds = None
    
    # Load existing token if available
    if os.path.exists(YOUTUBE_TOKEN_FILE):
        with open(YOUTUBE_TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # Check if credentials have all required scopes
    needs_reauth = False
    if creds and creds.valid:
        # Check if all required scopes are present
        token_scopes = set(creds.scopes if creds.scopes else [])
        required_scopes = set(YOUTUBE_SCOPES)
        if not required_scopes.issubset(token_scopes):
            print(f"  ⚠ Token missing required scopes. Need to re-authenticate.")
            print(f"     Required: {YOUTUBE_SCOPES}")
            print(f"     Current: {list(token_scopes)}")
            needs_reauth = True
    
    # If there are no valid credentials or missing scopes, request authorization
    if not creds or not creds.valid or needs_reauth:
        if creds and creds.expired and creds.refresh_token and not needs_reauth:
            creds.refresh(Request())
        else:
            if not os.path.exists(YOUTUBE_CLIENT_SECRETS_FILE):
                raise FileNotFoundError(
                    f"OAuth2 client secrets file not found: {YOUTUBE_CLIENT_SECRETS_FILE}\n"
                    "Please download it from Google Cloud Console and save it as 'client_secrets.json'"
                )
            if needs_reauth:
                print(f"  ℹ Re-authenticating to get required scopes...")
            flow = InstalledAppFlow.from_client_secrets_file(
                YOUTUBE_CLIENT_SECRETS_FILE, YOUTUBE_SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(YOUTUBE_TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('youtube', 'v3', credentials=creds)

def get_latest_scheduled_video(youtube_service=None):
    """
    Fetch the latest scheduled video from the YouTube channel
    
    Args:
        youtube_service: Authenticated YouTube service (if None, will authenticate)
    
    Returns:
        Tuple of (scheduled_datetime, video_index, kural_number) or (None, 0, 0) if not found
        scheduled_datetime: datetime object with timezone
        video_index: The calculated index position in the sequence (1-based)
        kural_number: The kural number from the video title (0 if not found)
    """
    from datetime import datetime, timedelta
    import pytz
    import re
    
    try:
        if youtube_service is None:
            youtube_service = get_authenticated_service()
        
        # Try to get channel ID first using mine=True
        channel_id = None
        uploads_playlist_id = None
        try:
            channels_response = youtube_service.channels().list(
                part='contentDetails',
                mine=True
            ).execute()
            
            if channels_response.get('items'):
                channel_id = channels_response['items'][0]['id']
                uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        except Exception as e:
            print(f"  ⚠ Could not get channel info with mine=True: {e}")
            print(f"  ℹ Trying alternative method to fetch videos...")
        
        # Fetch videos - try multiple methods
        videos_response = None
        
        # Method 1: If we have uploads playlist ID, use that (most reliable for scheduled videos)
        if uploads_playlist_id:
            try:
                print("  Trying to fetch videos from uploads playlist...")
                # Get playlist items
                playlist_items = youtube_service.playlistItems().list(
                    part='snippet,contentDetails',
                    playlistId=uploads_playlist_id,
                    maxResults=50
                ).execute()
                
                # Extract video IDs
                video_ids = [item['contentDetails']['videoId'] for item in playlist_items.get('items', [])]
                
                if video_ids:
                    print(f"  Found {len(video_ids)} videos in uploads playlist")
                    # Get video details including status (needed for scheduledPublishTime)
                    videos_response = youtube_service.videos().list(
                        part='status,snippet',
                        id=','.join(video_ids[:50])  # Limit to 50 videos
                    ).execute()
                    print(f"  Retrieved details for {len(videos_response.get('items', []))} videos")
            except Exception as e:
                print(f"  ⚠ Could not fetch videos from uploads playlist: {e}")
        
        # Method 2: Try using myRating='none' (requires youtube.force-ssl scope)
        # Note: This might not return scheduled videos, but worth trying
        if not videos_response:
            try:
                print("  Trying to fetch videos using myRating method...")
                videos_response = youtube_service.videos().list(
                    part='status,snippet',
                    myRating='none',  # Get our own videos
                    maxResults=50  # Get last 50 videos to find scheduled ones
                ).execute()
                if videos_response.get('items'):
                    print(f"  Retrieved {len(videos_response.get('items', []))} videos using myRating")
            except Exception as e:
                print(f"  ⚠ Could not fetch videos with myRating: {e}")
        
        if not videos_response or not videos_response.get('items'):
            print("  ⚠ Could not fetch videos from YouTube")
            print("     This might mean:")
            print("     - No videos have been uploaded yet")
            print("     - Authentication scopes are insufficient")
            print("     - Will use last_kural.txt file instead")
            return None, 0, 0
        
        latest_scheduled = None
        latest_scheduled_time = None
        latest_video_title = None
        
        # Debug: Check what we're getting
        print(f"  Analyzing {len(videos_response.get('items', []))} videos for scheduled ones...")
        scheduled_count = 0
        private_count = 0
        
        # Find the latest scheduled video
        # First pass: check all videos for scheduledPublishTime
        for video in videos_response.get('items', []):
            status = video.get('status', {})
            privacy_status = status.get('privacyStatus', '')
            scheduled_publish_time = status.get('scheduledPublishTime')
            snippet = video.get('snippet', {})
            video_title = snippet.get('title', 'Unknown')
            video_id = video.get('id', '')
            
            # Debug: Count private videos
            if privacy_status == 'private':
                private_count += 1
            
            # Check for scheduled publish time
            if scheduled_publish_time:
                scheduled_count += 1
                # Parse the scheduled time
                try:
                    # YouTube returns in RFC 3339 format
                    scheduled_dt = datetime.fromisoformat(scheduled_publish_time.replace('Z', '+00:00'))
                    
                    # Convert to our timezone
                    tz = pytz.timezone(YOUTUBE_TIMEZONE)
                    if scheduled_dt.tzinfo is None:
                        scheduled_dt = pytz.UTC.localize(scheduled_dt)
                    scheduled_dt = scheduled_dt.astimezone(tz)
                    
                    # Only consider future scheduled videos (not past ones)
                    now = datetime.now(tz)
                    if scheduled_dt > now:
                        # Track the latest one
                        if latest_scheduled_time is None or scheduled_dt > latest_scheduled_time:
                            latest_scheduled_time = scheduled_dt
                            latest_scheduled = scheduled_dt
                            latest_video_title = video_title
                            print(f"    Found scheduled video: '{video_title[:50]}...' for {scheduled_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                except Exception as e:
                    print(f"  ⚠ Error parsing scheduled time for video '{video_title[:50]}...': {e}")
                    continue
        
        # If no scheduledPublishTime found but we have private videos, try querying them individually
        # Sometimes the API doesn't return scheduledPublishTime in batch queries
        if not latest_scheduled and private_count > 0:
            print(f"  ℹ No scheduledPublishTime in batch query, trying individual video queries...")
            private_video_ids = []
            private_video_titles = {}
            
            # Collect private video IDs
            for video in videos_response.get('items', []):
                status = video.get('status', {})
                if status.get('privacyStatus', '') == 'private':
                    video_id = video.get('id', '')
                    if video_id:
                        private_video_ids.append(video_id)
                        snippet = video.get('snippet', {})
                        private_video_titles[video_id] = snippet.get('title', 'Unknown')
            
            # Query private videos individually to get full status
            if private_video_ids:
                print(f"  Querying {len(private_video_ids)} private videos individually...")
                # Query in batches of 50 (API limit)
                for i in range(0, len(private_video_ids), 50):
                    batch_ids = private_video_ids[i:i+50]
                    try:
                        batch_response = youtube_service.videos().list(
                            part='status,snippet',  # Include snippet to get title
                            id=','.join(batch_ids)
                        ).execute()
                        
                        for video in batch_response.get('items', []):
                            video_id = video.get('id', '')
                            status = video.get('status', {})
                            scheduled_publish_time = status.get('scheduledPublishTime')
                            
                            # Debug: Check what's in the status object
                            privacy_status = status.get('privacyStatus', '')
                            
                            # Also check for publishAt (alternative field name)
                            publish_at = status.get('publishAt')
                            if not scheduled_publish_time and publish_at:
                                scheduled_publish_time = publish_at
                            
                            if scheduled_publish_time:
                                scheduled_count += 1  # Update count
                                try:
                                    scheduled_dt = datetime.fromisoformat(scheduled_publish_time.replace('Z', '+00:00'))
                                    tz = pytz.timezone(YOUTUBE_TIMEZONE)
                                    if scheduled_dt.tzinfo is None:
                                        scheduled_dt = pytz.UTC.localize(scheduled_dt)
                                    scheduled_dt = scheduled_dt.astimezone(tz)
                                    
                                    now = datetime.now(tz)
                                    if scheduled_dt > now:
                                        if latest_scheduled_time is None or scheduled_dt > latest_scheduled_time:
                                            latest_scheduled_time = scheduled_dt
                                            latest_scheduled = scheduled_dt
                                            latest_video_title = private_video_titles.get(video_id, 'Unknown')
                                            print(f"    ✓ Found scheduled video (individual query): '{latest_video_title[:50]}...'")
                                            print(f"      Scheduled for: {scheduled_dt.strftime('%Y-%m-%d %H:%M:%S')} ({YOUTUBE_TIMEZONE})")
                                except Exception as e:
                                    print(f"  ⚠ Error parsing scheduled time: {e}")
                                    continue
                            else:
                                # Debug: Show what we got for private videos without scheduled time
                                if privacy_status == 'private' and i == 0:  # Only debug first batch to avoid spam
                                    snippet = video.get('snippet', {})
                                    title = snippet.get('title', 'Unknown')
                                    # Debug: Print status fields to see what's available
                                    if 'Thirukural 85' in title or len([v for v in batch_response.get('items', []) if v.get('id') == video_id]) == 1:
                                        print(f"    Debug - Video '{title[:50]}...':")
                                        print(f"      Status fields: {list(status.keys())}")
                                        print(f"      Privacy: {privacy_status}")
                                        print(f"      Upload status: {status.get('uploadStatus', 'N/A')}")
                                        print(f"      License: {status.get('license', 'N/A')}")
                                        print(f"      Embeddable: {status.get('embeddable', 'N/A')}")
                                        print(f"      Public stats: {status.get('publicStatsViewable', 'N/A')}")
                                        # Check if there's any date/time field
                                        for key, value in status.items():
                                            if 'time' in key.lower() or 'date' in key.lower() or 'publish' in key.lower():
                                                print(f"      {key}: {value}")
                    except Exception as e:
                        print(f"  ⚠ Error querying video batch: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
        
        print(f"  Summary: {scheduled_count} videos with scheduledPublishTime, {private_count} private videos")
        
        # If no scheduled videos found but we have private videos, check if any have publishAt in snippet
        if not latest_scheduled and private_count > 0:
            print(f"  ℹ No scheduledPublishTime found, but {private_count} private videos exist")
            print(f"     These might be scheduled but the API isn't returning scheduledPublishTime")
            print(f"     Extracting kural numbers from all videos to find the highest one...")
            
            # Extract kural numbers from all videos and find the highest one
            # This is more reliable than using publishedAt since videos might be uploaded out of order
            highest_kural = 0
            highest_kural_title = None
            kural_numbers_found = []
            
            for video in videos_response.get('items', []):
                snippet = video.get('snippet', {})
                video_title = snippet.get('title', 'Unknown')
                
                # Try to extract kural number from title
                match = re.search(r'Thirukural\s+(\d+)', video_title, re.IGNORECASE)
                if match:
                    try:
                        kural_num = int(match.group(1))
                        kural_numbers_found.append(kural_num)
                        if kural_num > highest_kural:
                            highest_kural = kural_num
                            highest_kural_title = video_title
                    except ValueError:
                        continue
            
            if highest_kural > 0:
                print(f"  ✓ Found {len(kural_numbers_found)} videos with kural numbers")
                print(f"  ✓ Highest kural number found: {highest_kural} (from '{highest_kural_title[:50]}...')")
                print(f"  ⚠ Could not get exact scheduled time from YouTube API")
                print(f"     Will use last_kural.txt to continue sequence")
                # Return None for scheduled datetime since we couldn't get exact time from YouTube
                return None, 0, highest_kural
            else:
                print(f"  ⚠ Could not extract kural numbers from any video titles")
        
        if latest_scheduled:
            print(f"  ✓ Found latest scheduled video: {latest_scheduled.strftime('%Y-%m-%d %H:%M:%S')} ({YOUTUBE_TIMEZONE})")
            
            # Extract kural number from title
            # Title format: "Thirukural {kural_number} | ..."
            kural_number = 0
            if latest_video_title:
                # Try to extract kural number from title
                # Pattern: "Thirukural" followed by a number
                match = re.search(r'Thirukural\s+(\d+)', latest_video_title, re.IGNORECASE)
                if match:
                    try:
                        kural_number = int(match.group(1))
                        print(f"  ✓ Extracted kural number from title: {kural_number}")
                    except ValueError:
                        print(f"  ⚠ Could not parse kural number from title: {latest_video_title}")
                else:
                    print(f"  ⚠ Could not find kural number in title: {latest_video_title}")
            
            # Calculate which position in the sequence this video was
            # We need to reverse-engineer the video_index from the scheduled time
            schedule_times = YOUTUBE_SCHEDULE_TIMES
            scheduled_hour = latest_scheduled.hour
            scheduled_minute = latest_scheduled.minute
            scheduled_time_str = f"{scheduled_hour:02d}:{scheduled_minute:02d}"
            
            # Find which time slot this matches
            try:
                time_index = schedule_times.index(scheduled_time_str)
            except ValueError:
                # If exact time not found, find closest match
                time_index = 0
                min_diff = float('inf')
                for i, time_str in enumerate(schedule_times):
                    h, m = map(int, time_str.split(':'))
                    diff = abs((h * 60 + m) - (scheduled_hour * 60 + scheduled_minute))
                    if diff < min_diff:
                        min_diff = diff
                        time_index = i
            
            # Calculate the day offset from the start date
            if YOUTUBE_SCHEDULE_START_DATE:
                try:
                    start_day = datetime.strptime(YOUTUBE_SCHEDULE_START_DATE, "%Y-%m-%d")
                    tz = pytz.timezone(YOUTUBE_TIMEZONE)
                    start_day = tz.localize(start_day.replace(hour=0, minute=0, second=0, microsecond=0))
                except:
                    start_day = latest_scheduled.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                start_day = latest_scheduled.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Calculate days difference
            days_diff = (latest_scheduled.date() - start_day.date()).days
            
            # Calculate video index: (days_diff * len(schedule_times)) + time_index + 1
            # +1 because video_index is 1-based
            video_index = (days_diff * len(schedule_times)) + time_index + 1
            
            print(f"  ✓ Calculated video index: {video_index} (day {days_diff + 1}, time slot {time_index + 1})")
            return latest_scheduled, video_index, kural_number
        else:
            print("  ⚠ No scheduled videos found, using default start date")
            return None, 0, 0
            
    except Exception as e:
        print(f"  ⚠ Error fetching latest scheduled video: {e}")
        import traceback
        traceback.print_exc()
        return None, 0, 0

def calculate_publish_date(video_index, start_date=None, schedule_times=None, base_video_index=0, base_scheduled_datetime=None):
    """
    Calculate the publish date for a video based on its index, cycling through multiple schedule times
    
    Args:
        video_index: Relative index of the video in current batch (1-based)
        start_date: Start date as string (YYYY-MM-DD) or None for today/tomorrow
        schedule_times: List of schedule times in 24-hour format (HH:MM), cycles through them
        base_video_index: The index of the last scheduled video (0 if none found)
        base_scheduled_datetime: The datetime of the last scheduled video (None if none found)
    
    Returns:
        RFC 3339 formatted datetime string for YouTube API
    """
    from datetime import datetime, timedelta
    import pytz
    
    # Use default schedule times if not provided
    if schedule_times is None:
        schedule_times = YOUTUBE_SCHEDULE_TIMES if hasattr(config, 'YOUTUBE_SCHEDULE_TIMES') else ["08:00"]
    
    # Get timezone
    try:
        tz = pytz.timezone(YOUTUBE_TIMEZONE)
    except:
        # Fallback to UTC if timezone not available
        tz = pytz.UTC
    
    # Determine start date
    now = datetime.now(tz)
    
    # If we have a base scheduled datetime, continue from there
    if base_scheduled_datetime and base_video_index > 0:
        # Find which time slot the base video was in
        base_hour = base_scheduled_datetime.hour
        base_minute = base_scheduled_datetime.minute
        base_time_str = f"{base_hour:02d}:{base_minute:02d}"
        
        # Find the base video's time slot index
        try:
            base_time_index = schedule_times.index(base_time_str)
        except ValueError:
            # If exact time not found, find closest match
            base_time_index = 0
            min_diff = float('inf')
            for i, time_str in enumerate(schedule_times):
                h, m = map(int, time_str.split(':'))
                diff = abs((h * 60 + m) - (base_hour * 60 + base_minute))
                if diff < min_diff:
                    min_diff = diff
                    base_time_index = i
        
        # Calculate how many videos after the base video this is
        videos_after_base = video_index
        
        # Calculate the next time slot index
        # Start from the slot after the base video's slot
        next_slot_index = (base_time_index + videos_after_base) % len(schedule_times)
        
        # Calculate which day this should be on
        # How many full cycles of schedule_times have passed
        total_slots_after_base = base_time_index + videos_after_base
        day_offset = total_slots_after_base // len(schedule_times)
        
        # Get the time for the next slot
        schedule_time = schedule_times[next_slot_index]
        hour, minute = map(int, schedule_time.split(':'))
        
        # Start from the base scheduled datetime's date
        base_date = base_scheduled_datetime.date()
        target_date = datetime.combine(base_date, datetime.min.time())
        target_date = tz.localize(target_date)
        
        # Add day offset
        target_date = target_date + timedelta(days=day_offset)
        
        # Set the time for this video
        publish_datetime = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Ensure we're scheduling in the future (at least one slot after base)
        if publish_datetime <= base_scheduled_datetime:
            # Move to next time slot
            if next_slot_index == len(schedule_times) - 1:
                # Last slot of the day, move to next day's first slot
                publish_datetime = (target_date + timedelta(days=1)).replace(
                    hour=int(schedule_times[0].split(':')[0]),
                    minute=int(schedule_times[0].split(':')[1]),
                    second=0,
                    microsecond=0
                )
            else:
                # Move to next time slot today
                next_time_index = next_slot_index + 1
                next_time = schedule_times[next_time_index]
                next_hour, next_minute = map(int, next_time.split(':'))
                publish_datetime = target_date.replace(hour=next_hour, minute=next_minute, second=0, microsecond=0)
        
        # Ensure we're not scheduling in the past
        if publish_datetime < now:
            # Find the next available time slot
            current_date = now.date()
            current_time = now.time()
            
            # Try today's remaining slots first
            found = False
            for time_str in schedule_times:
                h, m = map(int, time_str.split(':'))
                slot_time = datetime.combine(current_date, datetime.min.time().replace(hour=h, minute=m))
                slot_time = tz.localize(slot_time)
                
                if slot_time > now:
                    publish_datetime = slot_time
                    found = True
                    break
            
            # If no slots today, use first slot tomorrow
            if not found:
                first_time = schedule_times[0]
                h, m = map(int, first_time.split(':'))
                publish_datetime = datetime.combine(current_date + timedelta(days=1), datetime.min.time().replace(hour=h, minute=m))
                publish_datetime = tz.localize(publish_datetime)
        
        # Convert to RFC 3339 format (ISO 8601)
        return publish_datetime.isoformat()
    
    # Original logic if no base scheduled video found
    # Cycle through schedule times (0-based index, so video_index 1 uses times[0])
    time_index = (video_index - 1) % len(schedule_times)
    schedule_time = schedule_times[time_index]
    
    # Parse time
    hour, minute = map(int, schedule_time.split(':'))
    
    # Calculate which day this video should be published
    # Each day has len(schedule_times) slots (e.g., 4 slots per day: 8, 12, 3, 6)
    # Day number: (video_index - 1) // len(schedule_times)
    day_offset = (video_index - 1) // len(schedule_times)
    
    if start_date:
        try:
            # Parse start date and make it timezone-aware
            start_day = datetime.strptime(start_date, "%Y-%m-%d")
            start_day = tz.localize(start_day.replace(hour=0, minute=0, second=0, microsecond=0))
            
            # If start date is in the past, use today instead
            if start_day.date() < now.date():
                start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        except:
            # If invalid, use today
            start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Start from today
        start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate the target date (day_offset days from start_day)
    target_date = start_day + timedelta(days=day_offset)
    
    # Set the time for this video
    publish_datetime = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # If the scheduled time has already passed today, move to next occurrence
    if day_offset == 0 and publish_datetime < now:
        # If it's today and time has passed, check if we should use next time slot or next day
        # If this is the last time slot of the day, move to next day's first slot
        if time_index == len(schedule_times) - 1:
            # Last slot of today has passed, move to tomorrow's first slot
            publish_datetime = (target_date + timedelta(days=1)).replace(
                hour=int(schedule_times[0].split(':')[0]),
                minute=int(schedule_times[0].split(':')[1]),
                second=0,
                microsecond=0
            )
        else:
            # Use next time slot today
            next_time_index = time_index + 1
            next_time = schedule_times[next_time_index]
            next_hour, next_minute = map(int, next_time.split(':'))
            publish_datetime = target_date.replace(hour=next_hour, minute=next_minute, second=0, microsecond=0)
    
    # Convert to RFC 3339 format (ISO 8601)
    return publish_datetime.isoformat()

def validate_and_clean_tags(tags):
    """Validate and clean tags for YouTube API - strict validation to prevent errors"""
    import re
    valid_tags = []
    seen_tags = set()  # Track duplicates
    
    # YouTube tag restrictions:
    # - 2-30 characters
    # - Alphanumeric, hyphens, underscores only
    # - No spaces
    # - Case-insensitive duplicates not allowed
    # - Max 500 characters total for all tags combined
    
    total_length = 0
    max_total_length = 450  # Conservative limit (leave room for separators)
    
    for tag in tags:
        if not tag:
            continue
            
        # Convert to string and strip
        tag = str(tag).strip()
        
        # Skip if empty after stripping
        if not tag:
            continue
        
        # Remove all spaces
        tag = tag.replace(' ', '').replace('\t', '').replace('\n', '')
        
        # Remove all special characters except alphanumeric, hyphens, and underscores
        tag = re.sub(r'[^a-zA-Z0-9_-]', '', tag)
        
        # Skip if tag becomes empty after cleaning
        if not tag:
            continue
        
        # Limit to 30 characters (YouTube limit)
        if len(tag) > 30:
            tag = tag[:30]
        
        # Skip if tag is too short (YouTube requires at least 2 characters)
        if len(tag) < 2:
            continue
        
        # Skip if tag is too long (shouldn't happen after truncation, but double-check)
        if len(tag) > 30:
            continue
        
        # Skip duplicates (case-insensitive)
        tag_lower = tag.lower()
        if tag_lower in seen_tags:
            continue
        seen_tags.add(tag_lower)
        
        # Skip common problematic patterns and stop words
        stop_words = {'', 'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'}
        if tag_lower in stop_words:
            continue
        
        # Check if adding this tag would exceed total length limit
        if total_length + len(tag) > max_total_length:
            break  # Stop adding more tags if we're approaching the limit
        
        # Additional validation: ensure tag doesn't contain only numbers or only special chars
        if tag.replace('-', '').replace('_', '').isdigit():
            continue  # Skip tags that are only numbers
        
        if not re.search(r'[a-zA-Z0-9]', tag):
            continue  # Skip tags with no alphanumeric characters
        
        valid_tags.append(tag)
        total_length += len(tag)
    
    # Final limit: YouTube allows max 500 characters total for all tags
    # We'll be conservative and limit to 50 tags max
    return valid_tags[:50]

def upload_to_youtube(video_path, title, description="", tags=None, category_id=None, publish_at=None, default_language=None, default_audio_language=None):
    """
    Upload video to YouTube as Shorts with comprehensive metadata for maximum reach
    
    Args:
        video_path: Path to video file
        title: Video title
        description: Video description
        tags: List of tags
        category_id: Video category (27 = Education - optimal for wisdom/philosophy content)
        publish_at: RFC 3339 formatted datetime string for scheduling (None = publish immediately)
        default_language: Default language code (ta = Tamil)
        default_audio_language: Default audio language code (ta = Tamil)
    
    Returns:
        Video ID if successful, None otherwise
    """
    if not YOUTUBE_UPLOAD_ENABLED:
        print("  YouTube upload is disabled")
        return None
    
    # Use config defaults if not provided
    if category_id is None:
        category_id = config.YOUTUBE_CATEGORY_ID
    if default_language is None:
        default_language = config.YOUTUBE_DEFAULT_LANGUAGE
    if default_audio_language is None:
        default_audio_language = config.YOUTUBE_DEFAULT_AUDIO_LANGUAGE
    
    try:
        youtube = get_authenticated_service()
        
        # Prepare metadata
        # Validate and clean tags - ensure they're all valid before upload
        valid_tags = validate_and_clean_tags(tags) if tags else []
        
        # Additional safety check: ensure no invalid characters or patterns
        final_tags = []
        for tag in valid_tags:
            # Final validation pass
            if (tag and 
                isinstance(tag, str) and 
                len(tag) >= 2 and 
                len(tag) <= 30 and
                tag.replace('-', '').replace('_', '').isalnum() and
                not tag.isspace()):
                final_tags.append(tag)
        
        valid_tags = final_tags[:50]  # Final limit
        
        # Debug: print cleaned tags
        if valid_tags:
            print(f"  ✓ Using {len(valid_tags)} validated tags: {', '.join(valid_tags[:5])}{'...' if len(valid_tags) > 5 else ''}")
        else:
            print(f"  ⚠ No valid tags to use")
        
        # Prepare status object with all options for better reach
        status = {
            'privacyStatus': YOUTUBE_PRIVACY_STATUS,
            'selfDeclaredMadeForKids': False,
            'madeForKids': False,
            # Enable features for better engagement
            'publicStatsViewable': True
        }
        
        # Add publishAt if scheduling is enabled
        if publish_at:
            status['publishAt'] = publish_at
            print(f"  📅 Scheduled for: {publish_at}")
        
        # Comprehensive snippet with all metadata options
        # Only include tags if we have valid ones (YouTube rejects empty tag arrays)
        snippet = {
            'title': title,
            'description': description,
            'categoryId': category_id,
            'defaultLanguage': default_language,
            'defaultAudioLanguage': default_audio_language
        }
        
        # Add tags only if we have valid ones (and at least one)
        if valid_tags and len(valid_tags) > 0:
            snippet['tags'] = valid_tags
        # If no valid tags, don't include tags field at all (better than empty array)
        
        body = {
            'snippet': snippet,
            'status': status
        }
        
        # Insert video
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        insert_request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        # Upload video
        print(f"  Uploading to YouTube: {title}")
        response = None
        error = None
        retry = 0
        retry_without_tags = False  # Flag to retry without tags if tags are invalid
        
        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if response is not None:
                    if 'id' in response:
                        video_id = response['id']
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        print(f"  ✓ Uploaded successfully!")
                        print(f"  📺 Video URL: {video_url}")
                        return video_id
                    else:
                        error = f"Upload failed: {response}"
                        print(f"  ❌ {error}")
                        return None
            except Exception as e:
                error_str = str(e)
                # Check if error is due to invalid tags (shouldn't happen now with strict validation)
                if 'invalidTags' in error_str or 'invalid video keywords' in error_str.lower():
                    if not retry_without_tags and 'tags' in snippet:
                        print(f"  ⚠ Tags rejected by YouTube, retrying without tags...")
                        # Remove tags and retry
                        snippet.pop('tags', None)  # Remove tags key entirely
                        body = {
                            'snippet': snippet,
                            'status': status
                        }
                        # Recreate media object for retry
                        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
                        insert_request = youtube.videos().insert(
                            part=','.join(body.keys()),
                            body=body,
                            media_body=media
                        )
                        retry_without_tags = True
                        continue
                    else:
                        print(f"  ❌ Upload failed: {error_str}")
                        return None
                elif retry < 3:
                    retry += 1
                    print(f"  ⚠ Retry {retry}/3...")
                else:
                    error = error_str
                    print(f"  ❌ Upload error: {error}")
                    return None
        
    except FileNotFoundError as e:
        print(f"  ⚠ {e}")
        return None
    except Exception as e:
        print(f"  ❌ YouTube upload error: {e}")
        return None
    
    return None

# Initialize YouTube MCP Integration for metadata optimization
_mcp_integration = None
def get_mcp_integration_instance():
    """Get or create MCP integration instance"""
    global _mcp_integration
    if _mcp_integration is None and config.YOUTUBE_MCP_ENABLED:
        try:
            _mcp_integration = get_mcp_integration()
        except Exception as e:
            print(f"⚠ Warning: Could not initialize MCP integration: {e}")
            _mcp_integration = None
    return _mcp_integration

def get_optimized_metadata(kural_number, sentence, meaning, english_translation):
    """
    Get optimized metadata using YouTube MCP Server competitor analysis
    
    Args:
        kural_number: Kural number
        sentence: Tamil verse text
        meaning: Tamil meaning
        english_translation: English translation
        
    Returns:
        Dictionary with optimized title, description, and tags
    """
    # Default title (fallback if MCP is unavailable)
    default_title = f"Thirukural {kural_number} | Ancient Tamil Wisdom | {YOUTUBE_CHANNEL_NAME}"
    
    mcp = get_mcp_integration_instance()
    if not mcp or not mcp.client:
        # If MCP is not available, try to get keywords from direct search
        print(f"  ⚠ MCP client not available, using direct API search...")
        try:
            # Fallback: use direct YouTube API to search and extract keywords
            from googleapiclient.discovery import build
            youtube = build('youtube', 'v3', developerKey=config.YOUTUBE_API_KEY)
            
            # Search for videos
            search_response = youtube.search().list(
                q=f"Thirukural Tamil",
                part='snippet',
                maxResults=20,
                type='video'
            ).execute()
            
            # Extract keywords from titles
            all_keywords = []
            for item in search_response.get('items', []):
                title = item['snippet'].get('title', '')
                # Simple keyword extraction from titles
                words = title.lower().split()
                all_keywords.extend([w for w in words if len(w) > 3])
            
            from collections import Counter
            keyword_counts = Counter(all_keywords)
            top_keywords_raw = [word for word, count in keyword_counts.most_common(50)]
            
            # Clean keywords
            top_keywords = []
            import re
            for keyword in top_keywords_raw:
                clean_keyword = re.sub(r'[^a-zA-Z0-9]', '', keyword.replace(' ', ''))
                if (clean_keyword and len(clean_keyword) >= 2 and len(clean_keyword) <= 30 and
                    clean_keyword.isalnum() and clean_keyword.lower() not in [k.lower() for k in top_keywords]):
                    top_keywords.append(clean_keyword)
                    if len(top_keywords) >= 30:
                        break
        except Exception as e:
            print(f"  ⚠ Could not get keywords: {e}")
            top_keywords = []
    
    # Always use MCP if available, otherwise use fallback keywords
    if mcp and mcp.client:
        try:
            print(f"  🔍 Analyzing competitors for optimal metadata...")
            
            # Search queries to analyze - expanded to get more keywords
            search_queries = [
                f"Thirukural {kural_number}",
                "Thirukural Tamil wisdom",
                "Thirukural explanation Tamil",
                "Tamil wisdom quotes",
                "Thirukural meaning",
                "Tamil philosophy",
                "Ancient Tamil wisdom",
                "Thirukural teachings"
            ]
            
            # Collect keywords from competitor analysis - aim for at least 30 keywords
            all_keywords = []
            top_titles = []
            avg_views = []
            
            # Analyze more queries to get at least 30 keywords
            for query in search_queries[:6]:  # Use more queries to get more keywords
                try:
                    analysis = mcp.analyze_competitor_content(query, max_results=10)  # More results per query
                    if analysis:
                        keywords = analysis.get('top_keywords', [])
                        all_keywords.extend(keywords)
                        titles = analysis.get('sample_titles', [])
                        top_titles.extend(titles[:3])  # Top 3 titles per query
                        views = analysis.get('average_views', 0)
                        if views > 0:
                            avg_views.append(views)
                    
                    # If we have enough keywords, we can stop early
                    if len(set(all_keywords)) >= 30:
                        break
                except Exception as e:
                    print(f"    ⚠ Analysis error for '{query}': {e}")
                    continue
            
            # Get most common keywords - get at least 30
            from collections import Counter
            keyword_counts = Counter(all_keywords)
            # Get top 50 keywords to ensure we have at least 30 after cleaning
            top_keywords_raw = [word for word, count in keyword_counts.most_common(50)]
            
            # Clean and validate keywords to get at least 30 valid ones
            top_keywords = []
            for keyword in top_keywords_raw:
                # Clean keyword
                import re
                clean_keyword = keyword.replace(' ', '').replace('-', '').replace('_', '')
                clean_keyword = re.sub(r'[^a-zA-Z0-9]', '', clean_keyword)
                
                # Validate
                if (clean_keyword and 
                    len(clean_keyword) >= 2 and 
                    len(clean_keyword) <= 30 and
                    clean_keyword.isalnum() and
                    clean_keyword.lower() not in [k.lower() for k in top_keywords]):
                    top_keywords.append(clean_keyword)
                    
                    # Stop when we have at least 30
                    if len(top_keywords) >= 30:
                        break
            
            # Continue searching if we don't have 30 keywords yet
            # Try additional searches to get more keywords
            if len(top_keywords) < 30:
                additional_queries = [
                    "Tamil culture wisdom",
                    "Ancient Indian philosophy",
                    "Spiritual wisdom Tamil",
                    "Moral teachings Tamil"
                ]
                for query in additional_queries:
                    try:
                        analysis = mcp.analyze_competitor_content(query, max_results=10)
                        if analysis:
                            keywords = analysis.get('top_keywords', [])
                            for keyword in keywords:
                                clean_keyword = keyword.replace(' ', '').replace('-', '').replace('_', '')
                                import re
                                clean_keyword = re.sub(r'[^a-zA-Z0-9]', '', clean_keyword)
                                if (clean_keyword and len(clean_keyword) >= 2 and len(clean_keyword) <= 30 and
                                    clean_keyword.isalnum() and clean_keyword.lower() not in [k.lower() for k in top_keywords]):
                                    top_keywords.append(clean_keyword)
                                    if len(top_keywords) >= 30:
                                        break
                        if len(top_keywords) >= 30:
                            break
                    except:
                        continue
            
            # Use ONLY MCP keywords for tags (no static tags)
            enhanced_tags = []
            for keyword in top_keywords:
                # Clean and format keyword properly
                clean_keyword = keyword.replace(' ', '').replace('-', '').replace('_', '')
                # Remove special characters and ensure it's valid
                import re
                clean_keyword = re.sub(r'[^a-zA-Z0-9]', '', clean_keyword)
                # Validate: must be 2-30 chars, alphanumeric only, not duplicate
                if (clean_keyword and 
                    len(clean_keyword) >= 2 and 
                    len(clean_keyword) <= 30 and
                    clean_keyword.lower() not in [t.lower() for t in enhanced_tags] and
                    clean_keyword.isalnum()):
                    enhanced_tags.append(clean_keyword)
            
            # Validate all tags before returning (use the existing validation function)
            enhanced_tags = validate_and_clean_tags(enhanced_tags)
            
            # Limit tags to 50 (YouTube limit) - already handled by validate_and_clean_tags
            enhanced_tags = enhanced_tags[:50]
            
            # Optimize title based on competitor analysis
            # Try to incorporate top keywords while keeping it under 60 chars for Shorts
            optimized_title = default_title
            
            if top_keywords:
                # Try to create a more optimized title
                # Format: "Thirukural {num} | {top_keyword} | {channel}"
                top_keyword = top_keywords[0].title() if top_keywords else ""
                if top_keyword and len(top_keyword) < 20:
                    optimized_title = f"Thirukural {kural_number} | {top_keyword} Wisdom | {YOUTUBE_CHANNEL_NAME}"
                    # Ensure title is under 60 chars for Shorts
                    if len(optimized_title) > 60:
                        optimized_title = default_title
            
            print(f"  ✓ Metadata optimized using competitor analysis")
            print(f"    Found {len(top_keywords)} keywords (target: 30+)")
            print(f"    Top keywords: {', '.join(top_keywords[:10])}")
            if avg_views:
                print(f"    Average competitor views: {sum(avg_views)/len(avg_views):,.0f}")
            
            # Format keywords for description and hashtags
            # Keywords as comma-separated list for description
            keywords_text = ', '.join(top_keywords[:30])
            
            # Keywords as hashtags (with # prefix)
            hashtags = ' '.join([f"#{kw}" for kw in top_keywords[:30]])
            
            return {
                'title': optimized_title,
                'tags': enhanced_tags,
                'top_keywords': top_keywords[:30],  # Return all 30 keywords
                'keywords_text': keywords_text,  # For description
                'hashtags': hashtags,  # For description hashtags section
                'use_mcp': True
            }
            
        except Exception as e:
            print(f"  ⚠ Error optimizing metadata with MCP: {e}")
            # If MCP fails, use fallback keywords we got earlier
            if 'top_keywords' not in locals() or len(top_keywords) < 30:
                top_keywords = []
    
    # If we don't have enough keywords, use what we have
    if 'top_keywords' not in locals() or len(top_keywords) < 10:
        print(f"  ⚠ Not enough keywords found, using available keywords")
        top_keywords = top_keywords if 'top_keywords' in locals() else []
    
    # Format keywords for description and hashtags (use what we have, minimum 30)
    keywords_text = ', '.join(top_keywords[:30]) if len(top_keywords) >= 30 else ', '.join(top_keywords)
    hashtags = ' '.join([f"#{kw}" for kw in top_keywords[:30]]) if len(top_keywords) >= 30 else ' '.join([f"#{kw}" for kw in top_keywords])
    
    # Use ONLY MCP keywords for tags (no static tags)
    enhanced_tags = []
    for keyword in top_keywords:
        # Clean and format keyword properly
        clean_keyword = keyword.replace(' ', '').replace('-', '').replace('_', '')
        # Remove special characters and ensure it's valid
        import re
        clean_keyword = re.sub(r'[^a-zA-Z0-9]', '', clean_keyword)
        # Validate: must be 2-30 chars, alphanumeric only, not duplicate
        if (clean_keyword and 
            len(clean_keyword) >= 2 and 
            len(clean_keyword) <= 30 and
            clean_keyword.lower() not in [t.lower() for t in enhanced_tags] and
            clean_keyword.isalnum()):
            enhanced_tags.append(clean_keyword)
    
    # Validate all tags before returning
    enhanced_tags = validate_and_clean_tags(enhanced_tags)
    enhanced_tags = enhanced_tags[:50]
    
    # Optimize title
    optimized_title = default_title
    if top_keywords:
        top_keyword = top_keywords[0].title() if top_keywords else ""
        if top_keyword and len(top_keyword) < 20:
            optimized_title = f"Thirukural {kural_number} | {top_keyword} Wisdom | {YOUTUBE_CHANNEL_NAME}"
            if len(optimized_title) > 60:
                optimized_title = default_title
    
    return {
        'title': optimized_title,
        'tags': enhanced_tags,
        'top_keywords': top_keywords[:30],
        'keywords_text': keywords_text,
        'hashtags': hashtags,
        'use_mcp': mcp and mcp.client is not None
    }

# Functions to track last processed kural number
LAST_KURAL_FILE = os.path.join(os.path.dirname(__file__), "last_kural.txt")

def get_last_processed_kural():
    """Read the last processed kural number from file"""
    if os.path.exists(LAST_KURAL_FILE):
        try:
            with open(LAST_KURAL_FILE, 'r') as f:
                last_kural = int(f.read().strip())
                return last_kural
        except (ValueError, IOError):
            pass
    # If file doesn't exist or can't be read, start from kural 1
    return 0

def save_last_processed_kural(kural_number):
    """Save the last processed kural number to file"""
    try:
        with open(LAST_KURAL_FILE, 'w') as f:
            f.write(str(kural_number))
        print(f"  ✓ Saved last processed kural: {kural_number}")
    except IOError as e:
        print(f"  ⚠ Warning: Could not save last kural number: {e}")

# Main processing loop
def process_sentences():
    """Process all sentences: generate audio and create videos"""
    # Fetch latest scheduled video from YouTube to get kural number and schedule info
    base_scheduled_datetime = None
    base_video_index = 0
    youtube_kural = 0
    
    if YOUTUBE_UPLOAD_ENABLED and YOUTUBE_SCHEDULE_ENABLED:
        print("\n📡 Fetching latest scheduled video from YouTube channel...")
        try:
            # Authenticate first (this will block until user completes authentication if needed)
            print("  Authenticating with YouTube...")
            youtube_service = get_authenticated_service()
            print("  ✓ Authentication successful")
            
            # Now fetch the latest scheduled video
            base_scheduled_datetime, base_video_index, youtube_kural = get_latest_scheduled_video(youtube_service)
            
            if youtube_kural > 0:
                print(f"  ✓ Found kural {youtube_kural} in latest scheduled video")
            elif base_scheduled_datetime:
                print(f"  ✓ Found latest scheduled video but could not extract kural number")
            else:
                print(f"  ⚠ Could not find any scheduled videos")
        except KeyboardInterrupt:
            print(f"\n  ⚠ Authentication cancelled by user")
            print(f"  ℹ Will use last_kural.txt file instead")
            base_scheduled_datetime = None
            base_video_index = 0
            youtube_kural = 0
        except Exception as e:
            print(f"  ⚠ Error fetching latest scheduled video: {e}")
            print(f"  ℹ Will use last_kural.txt file instead")
            import traceback
            traceback.print_exc()
            base_scheduled_datetime = None
            base_video_index = 0
            youtube_kural = 0
    
    # Determine starting kural number
    # Prefer YouTube kural number if found, otherwise use last_kural.txt
    last_kural = get_last_processed_kural()
    
    if youtube_kural > 0:
        # Use YouTube kural number if it's higher than last_kural.txt (more recent)
        start_kural = max(youtube_kural, last_kural) + 1
        if youtube_kural > last_kural:
            print(f"  ✓ Using kural {youtube_kural} from YouTube (newer than last_kural.txt: {last_kural})")
        else:
            print(f"  ℹ Using last_kural.txt value {last_kural} (newer than YouTube: {youtube_kural})")
    else:
        # Fallback to last_kural.txt
        start_kural = last_kural + 1
        print(f"  ℹ Using last_kural.txt: starting from kural {start_kural}")
    
    # Get number of videos to process per run from config (always exactly this many)
    num_kurals = config.VIDEOS_PER_RUN if hasattr(config, 'VIDEOS_PER_RUN') else 10
    # Ensure it's a positive integer
    num_kurals = max(1, int(num_kurals))
    
    end_kural = start_kural + num_kurals - 1
    
    # Check if there are enough kurals to process
    total_available = len(sentences)
    if start_kural > total_available:
        print(f"\n{'='*60}")
        print(f"All {total_available} kurals have been processed!")
        print(f"Last processed: {last_kural}")
        print(f"{'='*60}\n")
        return
    
    # Adjust end_kural if we're near the end (but still try to process exactly num_kurals if possible)
    if end_kural > total_available:
        # If we can't get exactly num_kurals, process what's available
        end_kural = min(total_available, start_kural + num_kurals - 1)
        num_kurals = end_kural - start_kural + 1
        if num_kurals < config.VIDEOS_PER_RUN:
            print(f"  ℹ Note: Only {num_kurals} kurals remaining (requested {config.VIDEOS_PER_RUN}, available up to kural {total_available})")
    
    # Slice arrays to get only the kurals to process (0-based indices)
    start_index = start_kural - 1  # Convert to 0-based index
    end_index = start_index + num_kurals
    
    # Safety check: Never process more than configured VIDEOS_PER_RUN
    max_videos = config.VIDEOS_PER_RUN if hasattr(config, 'VIDEOS_PER_RUN') else 10
    num_kurals = min(num_kurals, max_videos)
    end_index = start_index + num_kurals
    
    sentences_to_process = sentences[start_index:end_index]
    meanings_to_process = meanings[start_index:end_index]
    english_translations_to_process = english_translations[start_index:end_index] if len(english_translations) > start_index else []
    
    total = len(sentences_to_process)
    
    # Final safety check: Ensure we don't process more than configured
    if total > max_videos:
        sentences_to_process = sentences_to_process[:max_videos]
        meanings_to_process = meanings_to_process[:max_videos]
        english_translations_to_process = english_translations_to_process[:max_videos] if len(english_translations_to_process) > max_videos else english_translations_to_process
        total = max_videos
        print(f"  ⚠ Safety limit: Processing exactly {max_videos} videos (configured limit)")
    
    # Reset font cache and load font once at start
    print("\nLoading font...")
    reset_font_cache()  # Clear any old cached fonts
    load_tamil_font(font_size, verbose=True)
    
    print(f"\n{'='*60}")
    print(f"Processing {total} videos per run (as configured)")
    print(f"Kurals: {start_kural} to {end_kural}")
    print(f"Last processed: {last_kural}")
    if youtube_kural > 0:
        print(f"Last YouTube scheduled: Kural {youtube_kural}")
    print(f"Videos per run: {config.VIDEOS_PER_RUN if hasattr(config, 'VIDEOS_PER_RUN') else 10}")
    if YOUTUBE_UPLOAD_ENABLED and YOUTUBE_SCHEDULE_ENABLED:
        print(f"\n📅 Scheduling Configuration:")
        if base_scheduled_datetime:
            print(f"   Continuing from latest scheduled video")
            print(f"   Base scheduled time: {base_scheduled_datetime.strftime('%Y-%m-%d %H:%M:%S')} ({YOUTUBE_TIMEZONE})")
            print(f"   Base video index: {base_video_index}")
        else:
            print(f"   Start Date: {YOUTUBE_SCHEDULE_START_DATE}")
        print(f"   Schedule Times: {', '.join(YOUTUBE_SCHEDULE_TIMES)} ({len(YOUTUBE_SCHEDULE_TIMES)} slots per day)")
        print(f"   Timezone: {YOUTUBE_TIMEZONE}")
        print(f"   Videos will cycle through time slots: {YOUTUBE_SCHEDULE_TIMES[0]} → {YOUTUBE_SCHEDULE_TIMES[1] if len(YOUTUBE_SCHEDULE_TIMES) > 1 else YOUTUBE_SCHEDULE_TIMES[0]} → ...")
    print(f"{'='*60}\n")
    
    last_processed = start_kural - 1  # Track last successfully processed kural
    
    for idx, sentence in enumerate(sentences_to_process):
        # Actual kural number
        i = start_kural + idx
        print(f"\n[Kural {i} ({idx+1}/{total})] Processing: {sentence}")
        print("-" * 60)
        
        # Calculate and display schedule date/time before processing (if scheduling enabled)
        if YOUTUBE_UPLOAD_ENABLED and YOUTUBE_SCHEDULE_ENABLED:
            try:
                relative_video_index = idx + 1
                publish_at_iso = calculate_publish_date(
                    relative_video_index, 
                    start_date=YOUTUBE_SCHEDULE_START_DATE,
                    schedule_times=YOUTUBE_SCHEDULE_TIMES,
                    base_video_index=base_video_index,
                    base_scheduled_datetime=base_scheduled_datetime
                )
                # Parse ISO format to display in readable format
                import pytz
                try:
                    publish_dt = datetime.fromisoformat(publish_at_iso)
                except ValueError:
                    publish_dt = datetime.fromisoformat(publish_at_iso.replace('+00:00', '').replace('Z', ''))
                
                # Convert to configured timezone for display
                tz = pytz.timezone(YOUTUBE_TIMEZONE)
                if publish_dt.tzinfo is None:
                    publish_dt = tz.localize(publish_dt)
                else:
                    publish_dt = publish_dt.astimezone(tz)
                
                # Extract the actual time slot from the calculated datetime
                scheduled_hour = publish_dt.hour
                scheduled_minute = publish_dt.minute
                scheduled_time_str = f"{scheduled_hour:02d}:{scheduled_minute:02d}"
                
                # Find which time slot this matches
                time_index = -1
                scheduled_time = scheduled_time_str
                
                # Try exact match first - iterate through schedule times to find match
                for i, time_str in enumerate(YOUTUBE_SCHEDULE_TIMES):
                    if time_str == scheduled_time_str:
                        time_index = i
                        scheduled_time = time_str
                        break
                
                # If exact match not found, find closest match
                if time_index < 0:
                    min_diff = float('inf')
                    best_match_index = 0
                    for i, time_str in enumerate(YOUTUBE_SCHEDULE_TIMES):
                        h, m = map(int, time_str.split(':'))
                        diff = abs((h * 60 + m) - (scheduled_hour * 60 + scheduled_minute))
                        if diff < min_diff:
                            min_diff = diff
                            best_match_index = i
                            scheduled_time = time_str
                    
                    time_index = best_match_index
                
                # Final validation - ensure time_index is valid
                if time_index < 0 or time_index >= len(YOUTUBE_SCHEDULE_TIMES):
                    # Last resort: match by hour and minute
                    for i, time_str in enumerate(YOUTUBE_SCHEDULE_TIMES):
                        h, m = map(int, time_str.split(':'))
                        if h == scheduled_hour and m == scheduled_minute:
                            time_index = i
                            scheduled_time = time_str
                            break
                
                print(f"📅 Scheduled for: {publish_dt.strftime('%Y-%m-%d %H:%M:%S')} ({YOUTUBE_TIMEZONE})")
                print(f"   Time slot: {scheduled_time} (slot {time_index + 1}/{len(YOUTUBE_SCHEDULE_TIMES)})")
            except Exception as e:
                print(f"⚠ Could not calculate schedule date: {e}")
                import traceback
                traceback.print_exc()
        
        # Generate audio filename
        audio_filename = f"audio_{i:03d}.wav"
        audio_path = os.path.join(audio_dir, audio_filename)
        
        # Generate video filename
        video_filename = f"video_{i:03d}.mp4"
        video_path = os.path.join(output_dir, video_filename)
        

        # Get meaning for this verse (use sliced array)
        meaning = meanings_to_process[idx] if idx < len(meanings_to_process) else ""
        
        # Step 1: Generate audio (with meaning included)
        generate_audio(sentence, audio_path, meaning)
        
        # Step 2: Create video (only verse text, not meaning) - pass kural number for adhigaram
        create_video(sentence, audio_path, video_path, kural_number=i)
        
        # Step 3: Upload to YouTube (if enabled)
        if YOUTUBE_UPLOAD_ENABLED:
            # Get optimized metadata using YouTube MCP Server
            metadata = get_optimized_metadata(
                i, 
                sentence, 
                meanings[i-1] if i <= len(meanings) else '',
                english_translations[i-1] if i <= len(english_translations) else ''
            )
            
            # Use optimized title from MCP analysis
            title = metadata.get('title', f"Thirukural {i} | Ancient Tamil Wisdom | {YOUTUBE_CHANNEL_NAME}")
            
            # Get optimized tags from MCP analysis
            tags = metadata.get('tags', [])
            
            # Get keywords and hashtags from MCP analysis (always use MCP, no static)
            keywords_text = metadata.get('keywords_text', '')
            hashtags = metadata.get('hashtags', '')
            top_keywords_list = metadata.get('top_keywords', [])
            
            # Build keywords section for description (30+ keywords from MCP)
            keywords_section = ""
            if keywords_text:
                keywords_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔑 KEYWORDS (30+ Optimized from Competitor Analysis):
{keywords_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            # Build hashtags section (30+ hashtags from MCP)
            hashtags_section = ""
            if hashtags:
                hashtags_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 HASHTAGS FOR MAXIMUM REACH (30+ Hashtags):
{hashtags}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            # Comprehensive description with MCP-optimized keywords and hashtags (NO static tags)
            description = f"""🌍 Ancient Wisdom for the Modern World | திருக்குறள் {i}

📖 Tamil Verse (தமிழ்):
{sentence}

💡 Detailed Meaning (விளக்கம்):
{meanings[i-1] if i <= len(meanings) else ''}

🌐 English Translation:
{english_translations[i-1] if i <= len(english_translations) else ''}
{keywords_section}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 {YOUTUBE_CHANNEL_NAME}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔔 Subscribe for Daily Wisdom: https://www.youtube.com/@{YOUTUBE_CHANNEL_NAME.replace(' ', '')}

We connect timeless Tamil wisdom to the world through:
✨ Thirukural teachings & explanations
📖 Ancient Tamil literature & philosophy
🎓 Education & continuous learning
💡 General knowledge & cultural insights
🌟 Life motivation & personal growth
📱 Daily wisdom in short, digestible formats

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 ENGAGE WITH US:
👍 Like this video if it inspired you!
💬 Comment your thoughts below
📤 Share with friends who need wisdom
🔔 Turn on notifications for daily content
{hashtags_section}"""
            
            # Calculate publish date if scheduling is enabled
            # Use relative index (0-based) within this batch, not absolute kural number
            publish_at = None
            if YOUTUBE_SCHEDULE_ENABLED:
                try:
                    # Use idx (0-based position in current batch) + 1 for 1-based offset
                    # Use configured start date from config.py
                    relative_video_index = idx + 1
                    publish_at = calculate_publish_date(
                        relative_video_index, 
                        start_date=YOUTUBE_SCHEDULE_START_DATE,  # Use configured start date from config.py
                        schedule_times=YOUTUBE_SCHEDULE_TIMES,  # Pass list of schedule times
                        base_video_index=base_video_index,
                        base_scheduled_datetime=base_scheduled_datetime
                    )
                    # Parse and display the full schedule date/time
                    import pytz
                    try:
                        publish_dt = datetime.fromisoformat(publish_at)
                    except ValueError:
                        publish_dt = datetime.fromisoformat(publish_at.replace('+00:00', '').replace('Z', ''))
                    tz = pytz.timezone(YOUTUBE_TIMEZONE)
                    if publish_dt.tzinfo is None:
                        publish_dt = tz.localize(publish_dt)
                    else:
                        publish_dt = publish_dt.astimezone(tz)
                    
                    # Extract the actual time slot from the calculated datetime
                    scheduled_hour = publish_dt.hour
                    scheduled_minute = publish_dt.minute
                    scheduled_time_str = f"{scheduled_hour:02d}:{scheduled_minute:02d}"
                    
                    # Find which time slot this matches
                    time_index = -1
                    scheduled_time = scheduled_time_str
                    
                    # Try exact match first - iterate through schedule times to find match
                    for i, time_str in enumerate(YOUTUBE_SCHEDULE_TIMES):
                        if time_str == scheduled_time_str:
                            time_index = i
                            scheduled_time = time_str
                            break
                    
                    # If exact match not found, find closest match
                    if time_index < 0:
                        min_diff = float('inf')
                        best_match_index = 0
                        for i, time_str in enumerate(YOUTUBE_SCHEDULE_TIMES):
                            h, m = map(int, time_str.split(':'))
                            diff = abs((h * 60 + m) - (scheduled_hour * 60 + scheduled_minute))
                            if diff < min_diff:
                                min_diff = diff
                                best_match_index = i
                                scheduled_time = time_str
                        
                        time_index = best_match_index
                        
                        # Debug: Show why exact match failed
                        if min_diff > 0:
                            print(f"  ⚠ Note: Scheduled time '{scheduled_time_str}' not found in schedule times {YOUTUBE_SCHEDULE_TIMES}")
                            print(f"     Using closest match: {scheduled_time} (slot {time_index + 1})")
                    
                    # Final validation - ensure time_index is valid
                    if time_index < 0 or time_index >= len(YOUTUBE_SCHEDULE_TIMES):
                        # Last resort: match by hour and minute
                        for i, time_str in enumerate(YOUTUBE_SCHEDULE_TIMES):
                            h, m = map(int, time_str.split(':'))
                            if h == scheduled_hour and m == scheduled_minute:
                                time_index = i
                                scheduled_time = time_str
                                break
                    
                    print(f"  📅 Scheduled for: {publish_dt.strftime('%Y-%m-%d %H:%M:%S')} ({YOUTUBE_TIMEZONE})")
                    print(f"     Time slot: {scheduled_time} (slot {time_index + 1}/{len(YOUTUBE_SCHEDULE_TIMES)})")
                except Exception as e:
                    print(f"  ⚠ Scheduling error: {e}, publishing immediately")
                    import traceback
                    traceback.print_exc()
                    publish_at = None
            
            # Upload with comprehensive metadata for maximum reach
            upload_to_youtube(
                video_path, 
                title, 
                description, 
                tags, 
                category_id=config.YOUTUBE_CATEGORY_ID,
                publish_at=publish_at,
                default_language=config.YOUTUBE_DEFAULT_LANGUAGE,
                default_audio_language=config.YOUTUBE_DEFAULT_AUDIO_LANGUAGE
            )
        
        print(f"✓ Completed: {sentence}")
        last_processed = i  # Update last processed kural after each successful completion
    
    # Save the last processed kural number for next run
    if last_processed > 0:
        save_last_processed_kural(last_processed)
    
    print(f"\n{'='*60}")
    print(f"✅ All {total} videos generated successfully!")
    print(f"📁 Videos saved in: {output_dir}/")
    print(f"📁 Audio files saved in: {audio_dir}/")
    print(f"📝 Last processed kural: {last_processed}")
    print(f"{'='*60}")

if __name__ == "__main__":
    try:
        process_sentences()
    except KeyboardInterrupt:
        print("\n⚠ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


