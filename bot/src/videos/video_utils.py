import os
import glob
from pathlib import Path
from bot.src.logger import logger

def get_videos_list(video_dir):
    """
    Get a list of video files from a directory
    
    Args:
        video_dir: Path to directory containing videos
        
    Returns:
        List of absolute paths to video files
    """
    logger.info(f"🔍 Searching for videos in directory: {video_dir}")
    
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    videos = []
    
    try:
        for ext in video_extensions:
            pattern = os.path.join(video_dir, f"*{ext}")
            videos.extend(glob.glob(pattern))
            
            # Also try case-insensitive match for extensions like .MP4
            pattern = os.path.join(video_dir, f"*{ext.upper()}")
            videos.extend(glob.glob(pattern))
            
        logger.info(f"[OK] Found {len(videos)} videos in directory")
        return videos
    except Exception as e:
        logger.error(f"[FAIL] Error finding videos: {str(e)}")
        return []

def get_videos_by_folders(root_dir):
    """
    Get videos organized by folders
    
    Args:
        root_dir: Root directory to search for videos
        
    Returns:
        Dictionary with folder names as keys and lists of video paths as values
    """
    logger.info(f"🔍 Searching for videos in subdirectories of: {root_dir}")
    
    videos_by_folder = {}
    
    try:
        # Get all subdirectories
        subdirs = [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))]
        
        for subdir in subdirs:
            folder_path = os.path.join(root_dir, subdir)
            videos = get_videos_list(folder_path)
            
            if videos:
                videos_by_folder[subdir] = videos
                
        logger.info(f"[OK] Found videos in {len(videos_by_folder)} subdirectories")
        return videos_by_folder
    except Exception as e:
        logger.error(f"[FAIL] Error finding videos by folders: {str(e)}")
        return {} 