# YouTube Upload Setup Guide

## Prerequisites

1. Install required Python packages:
```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## Setup Steps

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing one)
3. Enable **YouTube Data API v3**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click "Enable"

### 2. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure OAuth consent screen:
   - Choose "External" (unless you have Google Workspace)
   - Fill in required fields (app name, user support email, developer email)
   - Add scopes: `https://www.googleapis.com/auth/youtube.upload`
   - Save
4. Create OAuth client ID:
   - Application type: **Desktop app**
   - Name: "YouTube Uploader" (or any name)
   - Click "Create"
5. Download the JSON file
6. Rename it to `client_secrets.json` and place it in your project directory

### 3. Add Test Users (IMPORTANT for Testing)

Since your app is in testing mode, you must add test users. You can do this via **Google Cloud Shell** or the web UI:

#### Option A: Using Google Cloud Shell (Quick Commands)

1. Open **Google Cloud Console** and click the **Cloud Shell** icon (terminal icon) at the top
2. Run these commands:

```bash
# Set your email (replace with your actual email)
export TEST_EMAIL="your-email@gmail.com"

# Get your project ID
export PROJECT_ID=$(gcloud config get-value project)

# Open the OAuth consent screen directly (this opens in browser)
echo "Opening OAuth consent screen in browser..."
echo "1. Scroll to 'Test users' section"
echo "2. Click '+ ADD USERS'"
echo "3. Add email: $TEST_EMAIL"
echo "4. Click 'ADD' and 'SAVE'"
echo ""
echo "Direct link:"
echo "https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID"

# Alternative: You can also use the Python script provided
# python3 add_test_user.py $TEST_EMAIL
```

**Note**: Test users must be added via the web UI. The Cloud Shell helps you get the direct link quickly.

#### Option B: Using Web UI (Easier)

1. Go to **Google Cloud Console** > **APIs & Services** > **OAuth consent screen**
2. Scroll down to **Test users** section
3. Click **"+ ADD USERS"**
4. Add your Google account email address (the one you'll use to upload)
5. Click **"ADD"**
6. Save the changes

**Important**: Only the email addresses added here can authenticate and upload videos.

### 4. First Time Authentication

When you run the script for the first time:
1. A browser window will open
2. Sign in with your Google account (must be one of the test users)
3. You may see a warning - click "Continue" or "Advanced" > "Go to [your app name]"
4. Grant permissions to upload videos
5. The token will be saved in `token.pickle` for future use

**Note**: If you see "Access blocked: test has not completed Google verification":
- Make sure your email is added as a test user in step 3 above
- You may need to click "Advanced" > "Go to [app name]" to bypass the warning

### 5. Configuration

In `generate_batch_videos.py`, you can configure:
- `YOUTUBE_UPLOAD_ENABLED`: Set to `False` to disable uploads
- `YOUTUBE_PRIVACY_STATUS`: "public", "unlisted", or "private"
- `YOUTUBE_CHANNEL_NAME`: Your channel name
- Video titles, descriptions, and tags are automatically generated

### 6. YouTube Shorts Requirements

Your videos are automatically configured as Shorts because:
- Duration is 30 seconds (Shorts must be ≤ 60 seconds)
- Videos will be uploaded with appropriate tags

## Troubleshooting

### "Access blocked: test has not completed Google verification"
**SOLUTION**: 
1. Go to Google Cloud Console > APIs & Services > OAuth consent screen
2. Scroll to "Test users" section
3. Click "+ ADD USERS" and add your Google email
4. Save changes
5. Delete `token.pickle` if it exists
6. Run the script again and sign in with the test user email
7. When you see the warning, click "Advanced" > "Go to [your app name]"

### "client_secrets.json not found"
- Make sure you downloaded the OAuth credentials JSON file
- Rename it to exactly `client_secrets.json`
- Place it in the same directory as `generate_batch_videos.py`

### Authentication Errors
- Delete `token.pickle` and run again to re-authenticate
- Check that YouTube Data API v3 is enabled in your Google Cloud project
- Make sure your email is added as a test user

### Upload Fails
- Check your internet connection
- Verify your Google account has permission to upload videos
- Ensure you haven't exceeded YouTube's daily upload limits

