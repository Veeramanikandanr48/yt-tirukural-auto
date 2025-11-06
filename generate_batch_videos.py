from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.audio.AudioClip import CompositeAudioClip, AudioArrayClip
from moviepy.audio.fx.volumex import volumex
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
        
        # Extract meaning - include both Tamil meanings (exclude English from audio)
        meaning_obj = kural.get('meaning', {})
        meaning_parts = []
        
        # Add மு.வரதராசனார் meaning if available with proper punctuation
        if meaning_obj.get('ta_mu_va'):
            meaning_parts.append(f"மு.வரதராசனார் சொல்லுவது என்ன என்றால் , {meaning_obj['ta_mu_va']}")
        
        # Add சாலமன் பாப்பையா meaning if available with proper punctuation
        if meaning_obj.get('ta_salamon'):
            meaning_parts.append(f"சாலமன் பாப்பையா சொல்லுவது என்ன என்றால் , {meaning_obj['ta_salamon']}")
        
        # Combine meanings with comma and period for natural pauses (period creates longer pause)
        if meaning_parts:
            # Use period between meanings for longer pause, comma for shorter pauses within
            meanings.append(" . ".join(meaning_parts))
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
    """Format Tamil text with proper punctuation and pauses for clear TTS pronunciation"""
    if not text:
        return text
    
    # Add spaces around punctuation for better pronunciation
    # Replace multiple spaces with single space
    text = ' '.join(text.split())
    
    # Ensure proper spacing after commas and periods
    text = text.replace(',', ' , ')
    text = text.replace('.', ' . ')
    text = text.replace('?', ' ? ')
    text = text.replace('!', ' ! ')
    
    # Clean up multiple spaces
    text = ' '.join(text.split())
    
    return text

# Function to slow down audio for better clarity
def slow_down_audio(audio_data, sample_rate, speed_factor=0.85):
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

# Function to generate audio from text with emotion
def generate_audio(text, output_path, meaning=""):
    """Generate audio file from Tamil text using TTS with emotional expression and proper pronunciation"""
    # Combine verse and meaning if provided with proper punctuation
    if meaning:
        # Add proper pauses and formatting for Tamil TTS
        # Add longer pause after verse, then meaning introduction
        full_text = f"{text} . இதன் பொருள் என்ன என்றால், {meaning} ."
    else:
        full_text = f"{text} ."
    
    # Format text for better TTS pronunciation
    full_text = format_tamil_text_for_tts(full_text)
    
    print(f"\nGenerating audio for: {text}")

    if meaning:
        print(f"Including meaning: {meaning[:50]}...")
    
    inputs = tokenizer(full_text, return_tensors="pt")
    
    with torch.no_grad():
        output = model(**inputs).waveform  # tensor shape [1, samples]
    

    # Apply emotion adjustments (etram - uplifting, irkam - intensity)
    # Convert to numpy for processing
    audio_data = output.cpu().numpy()[0].astype(np.float32)
    
    # Normalize audio first
    max_val = np.max(np.abs(audio_data))
    if max_val > 0:
        audio_data = audio_data / max_val
    
    # Slow down audio slightly for better clarity and pronunciation (8% slower - slightly faster than before)
    sample_rate = model.config.sampling_rate
    audio_data = slow_down_audio(audio_data, sample_rate, speed_factor=0.92)
    
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
            bgm_looped = bgm_looped.fx(volumex, bgm_volume)
            
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
    
    # If there are no valid credentials, request authorization
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(YOUTUBE_CLIENT_SECRETS_FILE):
                raise FileNotFoundError(
                    f"OAuth2 client secrets file not found: {YOUTUBE_CLIENT_SECRETS_FILE}\n"
                    "Please download it from Google Cloud Console and save it as 'client_secrets.json'"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                YOUTUBE_CLIENT_SECRETS_FILE, YOUTUBE_SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(YOUTUBE_TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('youtube', 'v3', credentials=creds)

def calculate_publish_date(video_index, start_date=None, schedule_times=None):
    """
    Calculate the publish date for a video based on its index, cycling through multiple schedule times
    
    Args:
        video_index: Index of the video (1-based)
        start_date: Start date as string (YYYY-MM-DD) or None for today/tomorrow
        schedule_times: List of schedule times in 24-hour format (HH:MM), cycles through them
    
    Returns:
        RFC 3339 formatted datetime string for YouTube API
    """
    from datetime import datetime, timedelta
    import pytz
    
    # Use default schedule times if not provided
    if schedule_times is None:
        schedule_times = YOUTUBE_SCHEDULE_TIMES if hasattr(config, 'YOUTUBE_SCHEDULE_TIMES') else ["08:00"]
    
    # Cycle through schedule times (0-based index, so video_index 1 uses times[0])
    time_index = (video_index - 1) % len(schedule_times)
    schedule_time = schedule_times[time_index]
    
    # Parse time
    hour, minute = map(int, schedule_time.split(':'))
    
    # Get timezone
    try:
        tz = pytz.timezone(YOUTUBE_TIMEZONE)
    except:
        # Fallback to UTC if timezone not available
        tz = pytz.UTC
    
    # Determine start date
    now = datetime.now(tz)
    
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
    """Validate and clean tags for YouTube API"""
    import re
    valid_tags = []
    seen_tags = set()  # Track duplicates
    
    for tag in tags:
        if not tag:
            continue
            
        # Convert to string and strip
        tag = str(tag).strip()
        
        # Skip if empty after stripping
        if not tag:
            continue
        
        # Replace spaces with nothing (not underscores, as YouTube prefers no spaces)
        tag = tag.replace(' ', '')
        
        # Remove all special characters except alphanumeric, hyphens, and underscores
        tag = re.sub(r'[^a-zA-Z0-9_-]', '', tag)
        
        # Skip if tag becomes empty after cleaning
        if not tag:
            continue
        
        # Limit to 30 characters (YouTube limit)
        if len(tag) > 30:
            tag = tag[:30]
        
        # Skip if tag is too short (less than 2 characters might cause issues)
        if len(tag) < 2:
            continue
        
        # Skip duplicates (case-insensitive)
        tag_lower = tag.lower()
        if tag_lower in seen_tags:
            continue
        seen_tags.add(tag_lower)
        
        # Skip common problematic patterns
        if tag.lower() in ['', 'a', 'an', 'the', 'and', 'or', 'but']:
            continue
        
        valid_tags.append(tag)
    
    # Limit total tags to 50 (more conservative - YouTube recommends keeping it reasonable)
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
        # Validate and clean tags
        valid_tags = validate_and_clean_tags(tags) if tags else []
        
        # Debug: print cleaned tags
        print(f"  Using {len(valid_tags)} tags: {valid_tags[:10]}...")
        
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
        snippet = {
            'title': title,
            'description': description,
            'tags': valid_tags if valid_tags else None,
            'categoryId': category_id,
            'defaultLanguage': default_language,
            'defaultAudioLanguage': default_audio_language
        }
        
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
                # Check if error is due to invalid tags
                if 'invalidTags' in error_str or 'invalid video keywords' in error_str.lower():
                    if not retry_without_tags:
                        print(f"  ⚠ Invalid tags error detected, retrying without tags...")
                        # Retry without tags - recreate media and request
                        snippet['tags'] = None
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
                        print(f"  ❌ Upload failed even without tags: {error_str}")
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
    # Get last processed kural and start from the next one
    last_kural = get_last_processed_kural()
    start_kural = last_kural + 1  # Start from next kural after last processed
    
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
    print(f"Videos per run: {config.VIDEOS_PER_RUN if hasattr(config, 'VIDEOS_PER_RUN') else 10}")
    print(f"{'='*60}\n")
    
    last_processed = start_kural - 1  # Track last successfully processed kural
    
    for idx, sentence in enumerate(sentences_to_process):
        # Actual kural number
        i = start_kural + idx
        print(f"\n[Kural {i} ({idx+1}/{total})] Processing: {sentence}")
        print("-" * 60)
        
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
            # Create title and description with channel branding - optimized for global reach
            channel_name_english = YOUTUBE_CHANNEL_NAME  # Use the configured channel name
            
            # SEO-optimized title for better reach (under 60 chars for Shorts)
            title = f"Thirukural {i} | Ancient Tamil Wisdom | {YOUTUBE_CHANNEL_NAME}"
            
            # Comprehensive description with SEO, CTAs, and engagement elements
            description = f"""🌍 Ancient Wisdom for the Modern World | திருக்குறள் {i}

📖 Tamil Verse (தமிழ்):
{sentence}

💡 Detailed Meaning (விளக்கம்):
{meanings[i-1] if i <= len(meanings) else ''}

🌐 English Translation:
{english_translations[i-1] if i <= len(english_translations) else ''}

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️ KEYWORDS & HASHTAGS:
Thirukural, Thirukkural, Tamil Wisdom, Ancient Philosophy, Life Lessons, Spiritual Wisdom, Motivational Quotes, Self Improvement, Personal Growth, Education, Indian Culture, Eastern Philosophy, Wisdom Literature, Daily Wisdom, Inspirational Content, Mindfulness, Tamil Culture, Tamil Literature, Classical Tamil, Ethical Living, Moral Values, Life Philosophy, Wisdom Quotes, Spiritual Growth, Mental Health, Positive Thinking, Success Mindset, Life Motivation, Philosophy, Ethics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 GLOBAL HASHTAGS FOR REACH:
#Thirukural #Thirukkural #{YOUTUBE_CHANNEL_NAME.replace(' ', '')} #AncientWisdom #TamilWisdom #WorldWisdom #Philosophy #LifeLessons #WisdomQuotes #SpiritualWisdom #InspirationalQuotes #Mindfulness #SelfImprovement #PersonalGrowth #Motivation #Education #IndianPhilosophy #EasternWisdom #WisdomLiterature #Shorts #WisdomShorts #Worldwide #GlobalWisdom #UniversalWisdom #TimelessWisdom #DailyWisdom #TamilCulture #TamilLiterature #ClassicalTamil #EthicalLiving #MoralValues #LifePhilosophy #MentalHealth #PositiveThinking #SuccessMindset #LifeMotivation #Philosophy #Ethics #WisdomDaily #MotivationDaily #SelfHelp #PersonalDevelopment #SpiritualGrowth #MindfulLiving #TamilHeritage #CulturalWisdom #AncientTeachings #WisdomForLife #QuoteOfTheDay #DailyInspiration #WisdomWednesday #ShortsWisdom"""
            
            # Comprehensive tags optimized for YouTube Shorts reach
            tags = [
                # Primary keywords
                "Thirukural",
                "Thirukkural",
                "TamilWisdom",
                "AncientWisdom",
                "TamilPhilosophy",
                "TamilLiterature",
                # Topic keywords
                "LifeLessons",
                "MoralValues",
                "Ethics",
                "SpiritualWisdom",
                "SpiritualGrowth",
                "SelfImprovement",
                "PersonalGrowth",
                "Motivation",
                "Inspiration",
                "Mindfulness",
                "MentalHealth",
                "PositiveThinking",
                # Format keywords
                "Shorts",
                "QuickWisdom",
                # Cultural keywords
                "TamilCulture",
                "TamilHeritage",
                "IndianPhilosophy",
                "EasternWisdom",
                "ClassicalTamil",
                # Educational keywords
                "SelfHelp",
                "PersonalDevelopment",
                "LifeCoaching",
                # Engagement keywords
                "DailyWisdom",
                "WisdomQuotes",
                "QuoteOfTheDay",
                "DailyInspiration",
                "MotivationalQuotes",
                "InspirationalQuotes",
                # SEO keywords
                "AncientTeachings",
                "TimelessWisdom",
                "UniversalWisdom",
                "WorldWisdom",
                "WisdomForLife",
                "LifeMotivation",
                "SuccessMindset",
                "MindfulLiving",
                "EthicalLiving",
                "WisdomDaily"
            ]
            
            # Calculate publish date if scheduling is enabled
            # Use relative index (0-based) within this batch, not absolute kural number
            publish_at = None
            if YOUTUBE_SCHEDULE_ENABLED:
                try:
                    # Use idx (0-based position in current batch) + 1 for 1-based offset
                    # This ensures videos start from today, not from kural number days ahead
                    relative_video_index = idx + 1
                    publish_at = calculate_publish_date(
                        relative_video_index, 
                        start_date=None,  # Use None to always start from today/tomorrow
                        schedule_times=YOUTUBE_SCHEDULE_TIMES  # Pass list of schedule times
                    )
                    # Display which time slot this video is scheduled for
                    time_index = (relative_video_index - 1) % len(YOUTUBE_SCHEDULE_TIMES)
                    scheduled_time = YOUTUBE_SCHEDULE_TIMES[time_index]
                    print(f"  📅 Scheduled for: {scheduled_time} (slot {time_index + 1}/{len(YOUTUBE_SCHEDULE_TIMES)})")
                except Exception as e:
                    print(f"  ⚠ Scheduling error: {e}, publishing immediately")
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


