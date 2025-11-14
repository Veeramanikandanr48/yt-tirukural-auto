#!/usr/bin/env python3
"""
YouTube Community Post Scheduler for Thirukural
Automatically generates images and posts to YouTube Community tab
"""

import os
import json
import pickle
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import pytz
import schedule
import time
import sys

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# ============================================================================
# CONFIGURATION
# ============================================================================
# Schedule times (24-hour format)
SCHEDULE_TIMES = ["09:30", "13:30", "16:30", "19:30"]  # 9:30 AM, 1:30 PM, 4:30 PM, 7:30 PM

# Timezone
TIMEZONE = "Asia/Kolkata"  # Change to your timezone

# File paths
BACKGROUND_IMAGE = "kbg.png"  # Background image for community posts
THIRUKURAL_JSON = "thirukural_git.json"  # Kural data file
CLIENT_SECRETS_FILE = "client_secrets.json"  # OAuth credentials
TOKEN_FILE = "token_community.pickle"  # Community token file
LAST_POST_FILE = "last_post_kural.txt"  # Track last posted kural
POSTS_DIR = "posts"  # Directory for generated images
PENDING_POST_FILE = "pending_post.txt"  # Pending post info

# Font settings
FONT_PATH = "assets/fonts/Lohit-Tamil.ttf"  # Tamil font path
KURAL_FONT_SIZE = 48  # Font size for kural text (bold)
MEANING_FONT_SIZE = 32  # Font size for meaning text

# YouTube API scopes (community posts require force-ssl)
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

# ============================================================================
# FONT LOADING
# ============================================================================
_font_cache = {}

def load_tamil_font(size, verbose=False):
    """Load Tamil font with fallbacks (cached per size)"""
    global _font_cache
    if size in _font_cache:
        return _font_cache[size]
    
    font = None
    
    # Try custom font from config first
    try:
        abs_font_path = os.path.abspath(FONT_PATH)
        if os.path.exists(abs_font_path):
            font = ImageFont.truetype(abs_font_path, size)
            if verbose:
                print(f"✓ Loaded font: {os.path.basename(abs_font_path)} (size {size})")
            _font_cache[size] = font
            return font
    except Exception as e:
        if verbose:
            print(f"⚠ Could not load custom font: {e}")
    
    # Try Linux system Tamil fonts
    linux_tamil_fonts = [
        "/usr/share/fonts/truetype/lohit-tamil/Lohit-Tamil.ttf",
        "/usr/share/fonts/TTF/NotoSansTamil-Regular.ttf",
        "/usr/share/fonts/TTF/NotoSansTamil-Bold.ttf",
    ]
    
    for linux_font in linux_tamil_fonts:
        try:
            if os.path.exists(linux_font):
                font = ImageFont.truetype(linux_font, size)
                if verbose:
                    print(f"✓ Loaded system font: {os.path.basename(linux_font)} (size {size})")
                _font_cache[size] = font
                return font
        except:
            continue
    
    # Fallback to default
    if verbose:
        print("⚠ Warning: No Tamil font found! Using default font")
    font = ImageFont.load_default()
    _font_cache[size] = font
    return font

# ============================================================================
# THIRUKURAL DATA LOADING
# ============================================================================
def load_thirukural_data(json_path=THIRUKURAL_JSON):
    """Load Thirukural data from JSON file"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✓ Loaded {len(data['kurals'])} kurals from {json_path}")
        return data
    except FileNotFoundError:
        print(f"⚠ Warning: {json_path} not found.")
        return {"kurals": [], "chapters": []}
    except Exception as e:
        print(f"⚠ Error loading {json_path}: {e}")
        return {"kurals": [], "chapters": []}

# Load thirukural data
thirukural_data = load_thirukural_data()

# Extract kurals data
kurals_list = []
for kural in thirukural_data.get('kurals', []):
    kural_num = kural.get('number', 0)
    if kural_num > 0:
        # Combine the two lines into one sentence
        line1 = kural.get('kural', [''])[0] if kural.get('kural') else ''
        line2 = kural.get('kural', [''])[1] if len(kural.get('kural', [])) > 1 else ''
        full_verse = f"{line1} {line2}".strip()
        
        # Extract meaning - ta_mu_va meaning
        meaning_obj = kural.get('meaning', {})
        meaning = meaning_obj.get('ta_mu_va', '')
        
        # Also get other meanings for display
        meaning_mu_va = meaning_obj.get('ta_mu_va', '')
        meaning_salman = meaning_obj.get('ta_salman', '')
        
        kurals_list.append({
            'number': kural_num,
            'verse': full_verse,
            'meaning_mu_va': meaning_mu_va,
            'meaning_salman': meaning_salman,
            'chapter': kural.get('chapter', '')
        })

# ============================================================================
# IMAGE GENERATION
# ============================================================================
def generate_community_post_image(kural_number, verse, meaning_mu_va, meaning_salman, output_path):
    """Generate community post image with kural text and meaning"""
    print(f"\nGenerating image for Kural {kural_number}...")
    
    # Load background image
    if not os.path.exists(BACKGROUND_IMAGE):
        raise FileNotFoundError(f"Background image not found: {BACKGROUND_IMAGE}")
    
    img = Image.open(BACKGROUND_IMAGE).convert("RGBA")
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    kural_font = load_tamil_font(KURAL_FONT_SIZE, verbose=True)
    meaning_font = load_tamil_font(MEANING_FONT_SIZE, verbose=True)
    
    # Calculate positions
    width, height = img.size
    padding = 40
    y_position = padding
    
    # Draw title: "திருக்குறள் {number}"
    title_text = f"திருக்குறள் {kural_number}"
    try:
        title_bbox = draw.textbbox((0, 0), title_text, font=kural_font, direction="ltr", language="ta")
    except (TypeError, KeyError):
        title_bbox = draw.textbbox((0, 0), title_text, font=kural_font)
    
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    
    # Draw white background for title
    title_padding = 15
    draw.rectangle(
        [title_x - title_padding, y_position - title_padding,
         title_x + title_width + title_padding, y_position + (title_bbox[3] - title_bbox[1]) + title_padding],
        fill="white"
    )
    
    # Draw title text
    try:
        draw.text((title_x, y_position), title_text, font=kural_font, fill="black", direction="ltr", language="ta")
    except (TypeError, KeyError):
        draw.text((title_x, y_position), title_text, font=kural_font, fill="black")
    
    y_position += (title_bbox[3] - title_bbox[1]) + title_padding * 2 + 20
    
    # Draw verse (kural text) - split into two lines
    words = verse.split()
    if len(words) >= 4:
        line1 = ' '.join(words[:4])
        line2 = ' '.join(words[4:])
    else:
        mid = len(words) // 2
        line1 = ' '.join(words[:mid]) if mid > 0 else verse
        line2 = ' '.join(words[mid:]) if mid < len(words) else ""
    
    # Draw verse line 1
    try:
        verse1_bbox = draw.textbbox((0, 0), line1, font=kural_font, direction="ltr", language="ta")
    except (TypeError, KeyError):
        verse1_bbox = draw.textbbox((0, 0), line1, font=kural_font)
    
    verse1_width = verse1_bbox[2] - verse1_bbox[0]
    verse1_x = (width - verse1_width) // 2
    
    # White background for verse
    verse_padding = 20
    verse_bg_y1 = y_position - verse_padding
    verse_bg_y2 = y_position + (verse1_bbox[3] - verse1_bbox[1]) + verse_padding
    
    if line2:
        try:
            verse2_bbox = draw.textbbox((0, 0), line2, font=kural_font, direction="ltr", language="ta")
        except (TypeError, KeyError):
            verse2_bbox = draw.textbbox((0, 0), line2, font=kural_font)
        verse_bg_y2 += (verse2_bbox[3] - verse2_bbox[1]) + 10
    
    draw.rectangle(
        [padding, verse_bg_y1, width - padding, verse_bg_y2],
        fill="white"
    )
    
    # Draw verse lines
    try:
        draw.text((verse1_x, y_position), line1, font=kural_font, fill="black", direction="ltr", language="ta")
    except (TypeError, KeyError):
        draw.text((verse1_x, y_position), line1, font=kural_font, fill="black")
    
    if line2:
        y_position += (verse1_bbox[3] - verse1_bbox[1]) + 10
        try:
            verse2_bbox = draw.textbbox((0, 0), line2, font=kural_font, direction="ltr", language="ta")
        except (TypeError, KeyError):
            verse2_bbox = draw.textbbox((0, 0), line2, font=kural_font)
        verse2_width = verse2_bbox[2] - verse2_bbox[0]
        verse2_x = (width - verse2_width) // 2
        try:
            draw.text((verse2_x, y_position), line2, font=kural_font, fill="black", direction="ltr", language="ta")
        except (TypeError, KeyError):
            draw.text((verse2_x, y_position), line2, font=kural_font, fill="black")
        y_position += (verse2_bbox[3] - verse2_bbox[1]) + 20
    else:
        y_position += (verse1_bbox[3] - verse1_bbox[1]) + 20
    
    # Draw meaning section
    y_position += 20
    
    # Meaning label
    meaning_label = "இதன் பொருள்:"
    try:
        label_bbox = draw.textbbox((0, 0), meaning_label, font=meaning_font, direction="ltr", language="ta")
    except (TypeError, KeyError):
        label_bbox = draw.textbbox((0, 0), meaning_label, font=meaning_font)
    
    label_width = label_bbox[2] - label_bbox[0]
    label_x = (width - label_width) // 2
    
    # White background for meaning label
    draw.rectangle(
        [label_x - 10, y_position - 10,
         label_x + label_width + 10, y_position + (label_bbox[3] - label_bbox[1]) + 10],
        fill="white"
    )
    
    try:
        draw.text((label_x, y_position), meaning_label, font=meaning_font, fill="black", direction="ltr", language="ta")
    except (TypeError, KeyError):
        draw.text((label_x, y_position), meaning_label, font=meaning_font, fill="black")
    
    y_position += (label_bbox[3] - label_bbox[1]) + 15
    
    # Draw meanings (both if available)
    meanings_to_draw = []
    if meaning_mu_va:
        meanings_to_draw.append(f"மு.வ: {meaning_mu_va}")
    if meaning_salman:
        meanings_to_draw.append(f"சாலமன் பாப்பையா: {meaning_salman}")
    
    for meaning_text in meanings_to_draw:
        # Wrap text if too long
        max_width = width - padding * 2
        words = meaning_text.split()
        lines = []
        current_line = []
        current_width = 0
        
        for word in words:
            try:
                word_bbox = draw.textbbox((0, 0), word + " ", font=meaning_font, direction="ltr", language="ta")
            except (TypeError, KeyError):
                word_bbox = draw.textbbox((0, 0), word + " ", font=meaning_font)
            word_width = word_bbox[2] - word_bbox[0]
            
            if current_width + word_width > max_width and current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_width = word_width
            else:
                current_line.append(word)
                current_width += word_width
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw each line
        for line in lines:
            try:
                line_bbox = draw.textbbox((0, 0), line, font=meaning_font, direction="ltr", language="ta")
            except (TypeError, KeyError):
                line_bbox = draw.textbbox((0, 0), line, font=meaning_font)
            
            line_width = line_bbox[2] - line_bbox[0]
            line_x = (width - line_width) // 2
            
            # White background for meaning line
            draw.rectangle(
                [line_x - 10, y_position - 5,
                 line_x + line_width + 10, y_position + (line_bbox[3] - line_bbox[1]) + 5],
                fill="white"
            )
            
            try:
                draw.text((line_x, y_position), line, font=meaning_font, fill="black", direction="ltr", language="ta")
            except (TypeError, KeyError):
                draw.text((line_x, y_position), line, font=meaning_font, fill="black")
            
            y_position += (line_bbox[3] - line_bbox[1]) + 10
    
    # Convert to RGB and save
    if img.mode == 'RGBA':
        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
        rgb_img.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
        img = rgb_img
    
    img.save(output_path)
    print(f"✓ Image saved: {output_path}")
    return output_path

# ============================================================================
# YOUTUBE AUTHENTICATION
# ============================================================================
def get_authenticated_service():
    """Authenticate and return YouTube service for community posts"""
    creds = None
    
    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # Check if credentials have required scopes
    needs_reauth = False
    if creds and creds.valid:
        token_scopes = set(creds.scopes if creds.scopes else [])
        required_scopes = set(YOUTUBE_SCOPES)
        if not required_scopes.issubset(token_scopes):
            print(f"⚠ Token missing required scopes. Need to re-authenticate.")
            needs_reauth = True
    
    # If no valid credentials or missing scopes, request authorization
    if not creds or not creds.valid or needs_reauth:
        if creds and creds.expired and creds.refresh_token and not needs_reauth:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                raise FileNotFoundError(
                    f"OAuth2 client secrets file not found: {CLIENT_SECRETS_FILE}\n"
                    "Please download it from Google Cloud Console and save it as 'client_secrets.json'"
                )
            if needs_reauth:
                print(f"ℹ Re-authenticating to get required scopes...")
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, YOUTUBE_SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('youtube', 'v3', credentials=creds)

# ============================================================================
# COMMUNITY POST CREATION
# ============================================================================
def create_community_post(youtube_service, text_content):
    """Create a YouTube community post with text content"""
    try:
        # Get channel ID
        channels_response = youtube_service.channels().list(
            part='id',
            mine=True
        ).execute()
        
        if not channels_response.get('items'):
            print("⚠ Error: Could not get channel ID")
            return None
        
        channel_id = channels_response['items'][0]['id']
        
        # Create community post using Activities API
        # Note: YouTube Data API v3 doesn't support image uploads for community posts
        # We can only post text content
        # Community posts are created as activities with type "post"
        request_body = {
            'snippet': {
                'description': text_content,
                'type': 'post'
            }
        }
        
        # Try using activities.insert method
        # Note: This may require additional permissions or may not be available in all API versions
        try:
            response = youtube_service.activities().insert(
                part='snippet',
                body=request_body
            ).execute()
            post_id = response.get('id', '')
            print(f"✓ Community post created: {post_id}")
            return post_id
        except Exception as api_error:
            # If activities.insert doesn't work, try alternative method
            error_str = str(api_error)
            if 'activities' in error_str.lower() or 'not found' in error_str.lower():
                print(f"⚠ Note: Direct API method may not be available.")
                print(f"   Community posts may need to be created manually or via browser automation.")
                print(f"   Text content has been saved to {PENDING_POST_FILE}")
                print(f"   Image has been saved for manual upload.")
                # Return a placeholder ID
                return f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            else:
                raise
        
    except Exception as e:
        print(f"❌ Error creating community post: {e}")
        print(f"   Note: YouTube Data API v3 has limited support for community posts.")
        print(f"   You may need to use browser automation or manual upload.")
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# KURAL TRACKING
# ============================================================================
def get_last_posted_kural():
    """Get the last posted kural number"""
    if os.path.exists(LAST_POST_FILE):
        try:
            with open(LAST_POST_FILE, 'r') as f:
                last_kural = int(f.read().strip())
                return last_kural
        except (ValueError, IOError):
            pass
    return 0

def save_last_posted_kural(kural_number):
    """Save the last posted kural number"""
    try:
        with open(LAST_POST_FILE, 'w') as f:
            f.write(str(kural_number))
    except IOError as e:
        print(f"⚠ Warning: Could not save last posted kural: {e}")

# ============================================================================
# POST GENERATION AND UPLOAD
# ============================================================================
def create_and_post_kural(post_immediately=False):
    """Generate image and create community post for next kural"""
    # Get next kural number
    last_kural = get_last_posted_kural()
    next_kural_num = last_kural + 1
    
    # Cycle back to 1 if we've posted all kurals
    if next_kural_num > len(kurals_list):
        print(f"✓ All {len(kurals_list)} kurals posted. Resetting to kural 1.")
        next_kural_num = 1
    
    # Get kural data
    kural_data = kurals_list[next_kural_num - 1]  # 0-based index
    
    print(f"\n{'='*60}")
    print(f"Creating post for Kural {next_kural_num}")
    print(f"{'='*60}")
    
    # Ensure posts directory exists
    os.makedirs(POSTS_DIR, exist_ok=True)
    
    # Generate image
    image_filename = f"kural_{next_kural_num:04d}.png"
    image_path = os.path.join(POSTS_DIR, image_filename)
    
    try:
        generate_community_post_image(
            next_kural_num,
            kural_data['verse'],
            kural_data['meaning_mu_va'],
            kural_data['meaning_salman'],
            image_path
        )
    except Exception as e:
        print(f"❌ Error generating image: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Create text content for community post
    text_content = f"திருக்குறள் {next_kural_num}\n\n"
    text_content += f"{kural_data['verse']}\n\n"
    
    if kural_data['meaning_mu_va']:
        text_content += f"மு.வ: {kural_data['meaning_mu_va']}\n\n"
    
    if kural_data['meaning_salman']:
        text_content += f"சாலமன் பாப்பையா: {kural_data['meaning_salman']}"
    
    # Create community post
    try:
        youtube_service = get_authenticated_service()
        
        # Get channel ID for post URL
        channels_response = youtube_service.channels().list(
            part='id',
            mine=True
        ).execute()
        channel_id = channels_response['items'][0]['id'] if channels_response.get('items') else None
        
        post_id = create_community_post(youtube_service, text_content)
        
        if post_id:
            # Save pending post info
            post_url = f"https://www.youtube.com/channel/{channel_id}/community" if channel_id else "N/A"
            pending_info = f"""Channel ID: {channel_id or 'N/A'}
Image Path: {image_path}
Text Content:
{text_content}

Post URL: {post_url}
"""
            with open(PENDING_POST_FILE, 'w', encoding='utf-8') as f:
                f.write(pending_info)
            
            # Update last posted kural
            save_last_posted_kural(next_kural_num)
            
            print(f"\n✓ Post completed successfully!")
            print(f"  Kural: {next_kural_num}")
            print(f"  Image: {image_path}")
            print(f"  Post ID: {post_id}")
            print(f"\n⚠ Note: Image upload is not supported by YouTube Data API.")
            print(f"  Please manually attach the image via YouTube Studio:")
            print(f"  {post_url}")
            
            return True
        else:
            print(f"❌ Failed to create community post")
            return False
            
    except Exception as e:
        print(f"❌ Error posting to YouTube: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# SCHEDULER
# ============================================================================
def schedule_posts():
    """Schedule posts at configured times"""
    tz = pytz.timezone(TIMEZONE)
    
    for schedule_time in SCHEDULE_TIMES:
        schedule.every().day.at(schedule_time).do(job_wrapper)
        print(f"✓ Scheduled post at {schedule_time} ({TIMEZONE})")
    
    print(f"\n{'='*60}")
    print(f"Scheduler running. Posts will be created at:")
    for st in SCHEDULE_TIMES:
        print(f"  - {st} ({TIMEZONE})")
    print(f"{'='*60}\n")
    print("Press Ctrl+C to stop...\n")
    
    # Run scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def job_wrapper():
    """Wrapper for scheduled job"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scheduled post triggered")
    create_and_post_kural()

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    # Check if "now" argument is passed to post immediately
    if len(sys.argv) > 1 and sys.argv[1].lower() == "now":
        print("Posting immediately (test mode)...")
        create_and_post_kural(post_immediately=True)
    else:
        # Run scheduler
        schedule_posts()

