#!/usr/bin/env python3
"""
NASA Astronomy Picture of the Day (APOD) Wallpaper Updater for macOS
Secure, robust script with comprehensive error handling
"""

import os
import sys
import json
import logging
import tempfile
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, Any

# Only use built-in libraries for requests to avoid dependencies
import urllib.request
import urllib.error
import ssl
import shutil

# Configure logging
LOG_DIR = Path.home() / ".apod_wallpaper"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "apod_wallpaper.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
APOD_API_URL = "https://api.nasa.gov/planetary/apod"
ALLOWED_DOMAINS = {"nasa.gov", "api.nasa.gov", "apod.nasa.gov"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB max
IMAGE_CACHE_DIR = LOG_DIR / "images"
IMAGE_CACHE_DIR.mkdir(exist_ok=True)

# Image type detection without imghdr
IMAGE_SIGNATURES = {
    b'\xff\xd8\xff': 'jpeg',
    b'\x89PNG\r\n\x1a\n': 'png',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
    b'BM': 'bmp'
}
ALLOWED_IMAGE_TYPES = {'jpeg', 'png', 'gif', 'bmp'}


class APODWallpaperError(Exception):
    """Base exception for APOD wallpaper script"""
    pass


class SecurityError(APODWallpaperError):
    """Security-related errors"""
    pass


def get_api_key() -> str:
    """
    Get NASA API key from environment variable or use DEMO_KEY
    Store API key in environment: export NASA_API_KEY="your_key_here"
    """
    api_key = os.environ.get('NASA_API_KEY', 'DEMO_KEY')
    if api_key == 'DEMO_KEY':
        logger.warning("Using DEMO_KEY. For production use, get a free key at https://api.nasa.gov/")
    return api_key


def create_secure_context() -> ssl.SSLContext:
    """Create a secure SSL context for HTTPS requests"""
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def validate_url(url: str) -> None:
    """
    Validate URL for security
    - Must be HTTPS
    - Must be from allowed NASA domains
    """
    parsed = urlparse(url)
    
    if parsed.scheme != 'https':
        raise SecurityError(f"URL must use HTTPS: {url}")
    
    # Check if the hostname is in allowed domains or is a subdomain of nasa.gov
    hostname = parsed.netloc.lower()
    
    # Direct match
    if hostname in ALLOWED_DOMAINS:
        return
    
    # Check if it's a subdomain of nasa.gov
    if hostname.endswith('.nasa.gov'):
        return
    
    raise SecurityError(f"URL not from allowed domain: {url}")


def secure_download(url: str, max_size: int = MAX_FILE_SIZE) -> bytes:
    """
    Securely download content with size limits and timeout
    """
    validate_url(url)
    
    logger.info(f"Downloading from: {url}")
    
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'APOD-Wallpaper-Script/1.0 (https://github.com/nasa/apod-api)'
            }
        )
        
        context = create_secure_context()
        response = urllib.request.urlopen(
            req,
            context=context,
            timeout=30  # 30 second timeout
        )
        
        # Check content length
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > max_size:
            raise SecurityError(f"File too large: {content_length} bytes")
        
        # Read with size limit
        data = b''
        chunk_size = 8192
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            data += chunk
            if len(data) > max_size:
                raise SecurityError(f"Download exceeded size limit of {max_size} bytes")
        
        return data
        
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP error {e.code}: {e.reason}")
        raise APODWallpaperError(f"Failed to download: {e}")
    except urllib.error.URLError as e:
        logger.error(f"URL error: {e.reason}")
        raise APODWallpaperError(f"Network error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during download: {e}")
        raise


def fetch_apod_data(api_key: str) -> Dict[str, Any]:
    """Fetch APOD data from NASA API"""
    url = f"{APOD_API_URL}?api_key={api_key}"
    
    try:
        data = secure_download(url, max_size=1024 * 1024)  # 1MB max for JSON
        return json.loads(data.decode('utf-8'))
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response: {e}")
        raise APODWallpaperError("Invalid API response")


def detect_image_type(image_data: bytes) -> Optional[str]:
    """
    Detect image type from file signature (magic bytes)
    """
    for signature, image_type in IMAGE_SIGNATURES.items():
        if image_data.startswith(signature):
            return image_type
    return None


def validate_image(image_data: bytes) -> str:
    """
    Validate image data and return image type
    """
    # Check image header using signatures
    image_type = detect_image_type(image_data)
    if image_type not in ALLOWED_IMAGE_TYPES:
        raise SecurityError(f"Invalid or unsupported image type: {image_type}")
    
    return image_type


def save_image_securely(image_data: bytes, apod_data: Dict[str, Any]) -> Path:
    """
    Save image with secure filename and verify integrity
    """
    # Validate image
    image_type = validate_image(image_data)
    
    # Create secure filename with date
    date_str = apod_data.get('date', datetime.now().strftime('%Y-%m-%d'))
    # Sanitize date string
    date_str = ''.join(c for c in date_str if c.isalnum() or c == '-')
    
    # Add hash for uniqueness and integrity
    image_hash = hashlib.sha256(image_data).hexdigest()[:8]
    
    # Use proper extension
    extension = 'jpg' if image_type == 'jpeg' else image_type
    filename = f"apod_{date_str}_{image_hash}.{extension}"
    
    # Save to cache directory
    filepath = IMAGE_CACHE_DIR / filename
    
    # Use atomic write
    temp_fd, temp_path = tempfile.mkstemp(dir=IMAGE_CACHE_DIR)
    try:
        with os.fdopen(temp_fd, 'wb') as f:
            f.write(image_data)
        
        # Set secure permissions (read/write for owner only)
        os.chmod(temp_path, 0o600)
        
        # Atomic move
        shutil.move(temp_path, filepath)
        logger.info(f"Image saved: {filepath}")
        
        return filepath
        
    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except:
            pass
        raise APODWallpaperError(f"Failed to save image: {e}")


def set_wallpaper(image_path: Path) -> None:
    """
    Set desktop wallpaper using AppleScript (secure method for macOS)
    """
    script = f'''
    tell application "System Events"
        tell every desktop
            set picture to "{image_path}"
        end tell
    end tell
    '''
    
    try:
        # Use subprocess with proper escaping
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            raise APODWallpaperError(f"Failed to set wallpaper: {result.stderr}")
        
        logger.info("Wallpaper updated successfully")
        
    except subprocess.TimeoutExpired:
        raise APODWallpaperError("Timeout setting wallpaper")
    except Exception as e:
        raise APODWallpaperError(f"Error setting wallpaper: {e}")


def cleanup_old_images(keep_days: int = 7) -> None:
    """
    Clean up images older than specified days
    """
    try:
        cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
        
        for image_file in IMAGE_CACHE_DIR.glob("apod_*.*"):
            if image_file.stat().st_mtime < cutoff_time:
                image_file.unlink()
                logger.info(f"Cleaned up old image: {image_file}")
                
    except Exception as e:
        logger.warning(f"Error during cleanup: {e}")


def main():
    """Main function with comprehensive error handling"""
    try:
        logger.info("Starting APOD wallpaper update")
        
        # Get API key
        api_key = get_api_key()
        
        # Fetch APOD data
        apod_data = fetch_apod_data(api_key)
        
        # Check if today's APOD is an image
        media_type = apod_data.get('media_type', 'image')
        if media_type != 'image':
            logger.warning(f"Today's APOD is a {media_type}, not an image. Skipping.")
            return 0
        
        # Get image URL (prefer HD)
        image_url = apod_data.get('hdurl') or apod_data.get('url')
        if not image_url:
            raise APODWallpaperError("No image URL in API response")
        
        # Download image
        image_data = secure_download(image_url)
        
        # Save image securely
        image_path = save_image_securely(image_data, apod_data)
        
        # Set as wallpaper
        set_wallpaper(image_path)
        
        # Clean up old images
        cleanup_old_images()
        
        # Log success with image info
        logger.info(f"Successfully updated wallpaper: {apod_data.get('title', 'Unknown')}")
        
        return 0
        
    except APODWallpaperError as e:
        logger.error(f"Script error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())