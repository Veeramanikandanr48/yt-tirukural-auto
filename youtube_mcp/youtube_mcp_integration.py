"""
YouTube MCP Integration Module
Integrates YouTube MCP Server functionality into the video generation workflow
"""
import os
import sys
from typing import Optional, Dict, List, Any

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from .youtube_mcp_client import get_mcp_client, YouTubeMCPClient


class YouTubeMCPIntegration:
    """Integration class for YouTube MCP Server in video generation workflow"""
    
    def __init__(self):
        """Initialize YouTube MCP integration"""
        self.client = None
        if config.YOUTUBE_MCP_ENABLED and config.YOUTUBE_API_KEY:
            try:
                self.client = get_mcp_client(config.YOUTUBE_API_KEY)
                print("✓ YouTube MCP Client initialized")
            except Exception as e:
                print(f"⚠ Warning: Could not initialize YouTube MCP Client: {e}")
                print("  Continuing without MCP features (upload will still work)")
        else:
            if not config.YOUTUBE_MCP_ENABLED:
                print("ℹ YouTube MCP Server is disabled in config")
            elif not config.YOUTUBE_API_KEY:
                print("⚠ Warning: YOUTUBE_API_KEY not set. MCP features unavailable.")
    
    def get_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a YouTube video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Video information dictionary or None
        """
        if not self.client:
            return None
        
        try:
            return self.client.get_video(video_id)
        except Exception as e:
            print(f"⚠ Error getting video info: {e}")
            return None
    
    def search_related_videos(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for related videos (useful for finding similar content)
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of video dictionaries
        """
        if not self.client:
            return []
        
        try:
            return self.client.search_videos(query, max_results)
        except Exception as e:
            print(f"⚠ Error searching videos: {e}")
            return []
    
    def get_video_transcript(self, video_id: str, language: str = None) -> Optional[str]:
        """
        Get transcript for a YouTube video
        
        Args:
            video_id: YouTube video ID
            language: Language code (defaults to config.YOUTUBE_TRANSCRIPT_LANG)
            
        Returns:
            Transcript text or None
        """
        if not self.client:
            return None
        
        if language is None:
            language = config.YOUTUBE_TRANSCRIPT_LANG
        
        try:
            result = self.client.get_transcript(video_id, language)
            if result and 'transcript' in result:
                return result['transcript']
            return None
        except Exception as e:
            print(f"⚠ Error getting transcript: {e}")
            return None
    
    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get channel information
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            Channel information dictionary or None
        """
        if not self.client:
            return None
        
        try:
            return self.client.get_channel(channel_id)
        except Exception as e:
            print(f"⚠ Error getting channel info: {e}")
            return None
    
    def list_channel_videos(self, channel_id: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        List videos from a channel
        
        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of results
            
        Returns:
            List of video dictionaries
        """
        if not self.client:
            return []
        
        try:
            return self.client.list_channel_videos(channel_id, max_results)
        except Exception as e:
            print(f"⚠ Error listing channel videos: {e}")
            return []
    
    def analyze_competitor_content(self, search_query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Analyze competitor content for SEO and content strategy
        
        Args:
            search_query: Search query (e.g., "Thirukural Tamil")
            max_results: Maximum number of results to analyze
            
        Returns:
            Analysis dictionary with insights
        """
        if not self.client:
            return {}
        
        try:
            videos = self.search_related_videos(search_query, max_results)
            
            if not videos:
                return {}
            
            # Analyze titles, descriptions, etc.
            titles = []
            view_counts = []
            
            for video in videos:
                snippet = video.get('snippet', {})
                titles.append(snippet.get('title', ''))
                
                # Get detailed stats if available
                video_id = snippet.get('id', {}).get('videoId') if isinstance(snippet.get('id'), dict) else snippet.get('id')
                if video_id:
                    video_info = self.get_video_info(video_id)
                    if video_info:
                        stats = video_info.get('statistics', {})
                        view_count = int(stats.get('viewCount', 0))
                        view_counts.append(view_count)
            
            analysis = {
                'total_videos_found': len(videos),
                'average_views': sum(view_counts) / len(view_counts) if view_counts else 0,
                'sample_titles': titles[:5],
                'top_keywords': self._extract_keywords(titles)
            }
            
            return analysis
            
        except Exception as e:
            print(f"⚠ Error analyzing competitor content: {e}")
            return {}
    
    def _extract_keywords(self, titles: List[str]) -> List[str]:
        """Extract common keywords from titles"""
        # Simple keyword extraction (can be enhanced)
        from collections import Counter
        import re
        
        all_words = []
        for title in titles:
            # Split by common separators and get words
            words = re.findall(r'\b\w+\b', title.lower())
            all_words.extend(words)
        
        # Get most common words (excluding common stop words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'}
        filtered_words = [w for w in all_words if w not in stop_words and len(w) > 3]
        
        word_counts = Counter(filtered_words)
        return [word for word, count in word_counts.most_common(10)]


# Global instance
_mcp_integration = None


def get_mcp_integration() -> YouTubeMCPIntegration:
    """Get or create global YouTube MCP integration instance"""
    global _mcp_integration
    if _mcp_integration is None:
        _mcp_integration = YouTubeMCPIntegration()
    return _mcp_integration


# Example usage and helper functions
if __name__ == "__main__":
    # Example: Get video info
    integration = get_mcp_integration()
    
    # Example: Search for related videos
    print("\nSearching for 'Thirukural' videos...")
    videos = integration.search_related_videos('Thirukural Tamil', max_results=5)
    print(f"Found {len(videos)} videos")
    
    for video in videos:
        snippet = video.get('snippet', {})
        title = snippet.get('title', 'Unknown')
        print(f"  - {title}")
    
    # Example: Analyze competitor content
    print("\nAnalyzing competitor content...")
    analysis = integration.analyze_competitor_content('Thirukural Tamil wisdom', max_results=5)
    if analysis:
        print(f"Total videos found: {analysis.get('total_videos_found', 0)}")
        print(f"Average views: {analysis.get('average_views', 0):,.0f}")
        print(f"Top keywords: {', '.join(analysis.get('top_keywords', []))}")

