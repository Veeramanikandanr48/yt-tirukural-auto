# YouTube MCP Integration

This folder contains the Python integration for the [YouTube MCP Server](https://github.com/ZubeidHendricks/youtube-mcp-server).

## Files

- `youtube_mcp_client.py` - Core client for communicating with the YouTube MCP Server
- `youtube_mcp_integration.py` - High-level integration module for video generation workflow
- `mcp_bridge.js` - Node.js bridge script for Python-to-MCP communication
- `__init__.py` - Package initialization file

## Setup

1. **Install YouTube MCP Server** (already done):
   ```bash
   npm install -g zubeid-youtube-mcp-server
   ```

2. **Set YouTube API Key**:
   ```bash
   export YOUTUBE_API_KEY="your_api_key_here"
   ```
   
   Or set it in `config.py`:
   ```python
   YOUTUBE_API_KEY = "your_api_key_here"
   ```

3. **Enable MCP in config.py**:
   ```python
   YOUTUBE_MCP_ENABLED = True
   ```

## Usage

### Basic Usage

```python
from youtube_mcp import get_mcp_integration

# Get integration instance
integration = get_mcp_integration()

# Search for videos
videos = integration.search_related_videos('Thirukural Tamil', max_results=5)

# Get video info
video_info = integration.get_video_info('video_id_here')

# Get transcript
transcript = integration.get_video_transcript('video_id_here', language='en')

# Analyze competitor content
analysis = integration.analyze_competitor_content('Thirukural Tamil wisdom')
```

### Direct Client Usage

```python
from youtube_mcp import get_mcp_client

client = get_mcp_client(api_key='your_api_key')

# Get video details
video = client.get_video('video_id')

# Search videos
results = client.search_videos('query', max_results=10)

# Get channel info
channel = client.get_channel('channel_id')
```

## Features

- ✅ Video information retrieval
- ✅ Video search
- ✅ Channel information
- ✅ Video transcripts
- ✅ Channel video listing
- ✅ Competitor content analysis

## Notes

- The MCP server requires a YouTube Data API v3 key
- This is different from OAuth2 credentials used for video uploads
- If MCP server is unavailable, the client falls back to direct YouTube API calls
- Transcripts may require additional setup depending on video availability

## API Key Setup

Get your YouTube API key from:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project or select existing one
3. Enable YouTube Data API v3
4. Create API credentials (API key)
5. Copy the API key and set it as `YOUTUBE_API_KEY`



