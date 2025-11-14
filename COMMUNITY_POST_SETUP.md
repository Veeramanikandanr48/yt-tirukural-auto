# YouTube Community Post Scheduler Setup

This guide explains how to set up and use the YouTube Community Post Scheduler for daily Tirukural posts.

## Features

- ✅ Automatically generates images with Tirukural text and meaning on `kbg.png` background
- ✅ Schedules daily posts at 9:30 AM, 1:30 PM, 4:30 PM, and 7:30 PM
- ✅ Creates YouTube community posts with text content
- ✅ Tracks which kurals have been posted

## Prerequisites

1. Python 3.10+
2. YouTube channel with Community tab enabled
3. Google Cloud Project with YouTube Data API v3 enabled
4. OAuth 2.0 credentials (`client_secrets.json`)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure you have:
   - `kbg.png` in the project root (background image)
   - `thirukural_git.json` (kural data)
   - `client_secrets.json` (OAuth credentials)

## YouTube API Setup

1. **Enable YouTube Data API v3:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3" and enable it

2. **Create OAuth 2.0 Credentials:**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: **Desktop app**
   - Download the JSON file and save as `client_secrets.json`

3. **Required Scopes:**
   - `https://www.googleapis.com/auth/youtube.force-ssl` (for community posts)

## Usage

### Test Post (Post Immediately)

To test the system and post immediately:

```bash
python3 community_post_scheduler.py now
```

This will:
- Generate an image with the next kural
- Create a community post with text
- Save the image in the `posts/` directory

### Run Scheduler

To start the daily scheduler:

```bash
python3 community_post_scheduler.py
```

The scheduler will:
- Post at 9:30 AM, 1:30 PM, 4:30 PM, and 7:30 PM daily
- Use your configured timezone (default: Asia/Kolkata)
- Continue running until stopped (Ctrl+C)

### Run as Background Service

For production, run as a background service:

**Linux (systemd):**

Create `/etc/systemd/system/youtube-community-posts.service`:

```ini
[Unit]
Description=YouTube Community Post Scheduler
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/yt-tirukural-auto
ExecStart=/usr/bin/python3 /path/to/yt-tirukural-auto/community_post_scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable youtube-community-posts.service
sudo systemctl start youtube-community-posts.service
```

**Using screen/tmux:**
```bash
screen -S youtube-posts
python3 community_post_scheduler.py
# Press Ctrl+A then D to detach
```

## Image Upload Limitation

**Important:** YouTube Data API v3 does not support direct image uploads for community posts. The script will:

1. ✅ Generate images with kural text and meaning
2. ✅ Create text-based community posts
3. ⚠️ Save images to `posts/` directory (requires manual upload or browser automation)

### Options for Image Upload:

**Option 1: Manual Upload**
- Images are saved in `posts/kural_XXXX.png`
- Manually attach images via YouTube Studio after the text post is created

**Option 2: Browser Automation (Advanced)**
- Use Selenium or similar tools to automate image upload
- See `community_post_browser.py` (if created) for automation script

**Option 3: Image Hosting Service**
- Upload images to Imgur/Cloudinary/etc.
- Include image URL in the post text

## Configuration

Edit `community_post_scheduler.py` to customize:

- `SCHEDULE_TIMES`: Post times (24-hour format)
- `TIMEZONE`: Your timezone
- `KURAL_FONT_SIZE`: Font size for kural text
- `MEANING_FONT_SIZE`: Font size for meaning text
- `BACKGROUND_IMAGE`: Path to background image

## File Structure

```
yt-tirukural-auto/
├── community_post_scheduler.py  # Main scheduler script
├── kbg.png                      # Background image
├── posts/                       # Generated images
│   └── kural_0001.png
├── last_post_kural.txt          # Tracks last posted kural
└── thirukural_git.json          # Kural data
```

## Troubleshooting

### Authentication Issues

If you get authentication errors:
1. Delete `token.pickle` and re-authenticate
2. Ensure `client_secrets.json` is in the project root
3. Check that YouTube Data API v3 is enabled

### Font Issues

If Tamil text doesn't render correctly:
1. Ensure Tamil fonts are installed
2. Check `FONT_PATH` in the script
3. Fonts are loaded from: `assets/fonts/Lohit-Tamil.ttf`

### Schedule Not Running

- Check timezone settings
- Ensure script is running continuously
- Check system time is correct
- Verify schedule times are in 24-hour format

## Notes

- Posts cycle through all 1330 kurals
- After all kurals are posted, it resets to kural 1
- Images are generated with bold kural text and regular meaning text
- Each post includes kural number, verse, and meaning

## Support

For issues or questions, check:
- YouTube Data API v3 documentation
- Python `schedule` library documentation
- PIL/Pillow documentation for image generation
















