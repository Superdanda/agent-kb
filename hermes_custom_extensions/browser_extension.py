"""
Browser extension for Chrome CDP integration.
Supports macOS, Linux, and Windows Chrome launches.
"""
import os
import sys
import subprocess
import time
import socket
from typing import Optional, List

# Default CDP settings
DEFAULT_CDP_HOST = "127.0.0.1"
DEFAULT_CDP_PORT = 9222


def get_browser_cdp_host() -> str:
    """Get BROWSER_CDP_HOST from environment or use default."""
    return os.environ.get("BROWSER_CDP_HOST", DEFAULT_CDP_HOST)


def get_browser_cdp_port() -> int:
    """Get BROWSER_CDP_PORT from environment or use default."""
    port_str = os.environ.get("BROWSER_CDP_PORT", str(DEFAULT_CDP_PORT))
    try:
        return int(port_str)
    except ValueError:
        return DEFAULT_CDP_PORT


def set_browser_cdp_url(host: str, port: int) -> None:
    """Set BROWSER_CDP_URL environment variable after browser launch."""
    os.environ["BROWSER_CDP_URL"] = f"ws://{host}:{port}"


def _get_chrome_candidates() -> List[str]:
    """
    Get list of potential Chrome executable paths for the current OS.
    """
    candidates = []
    
    if sys.platform == "darwin":
        # macOS paths
        candidates.extend([
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chrome.app/Contents/MacOS/Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            os.path.expanduser("~/Applications/Chrome.app/Contents/MacOS/Chrome"),
        ])
    elif sys.platform == "linux":
        # Linux paths
        candidates.extend([
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
            os.path.expanduser("~/.local/share/google-chrome-stable/chrome"),
            os.path.expanduser("~/snap/chromium/common/chromium-browser"),
        ])
    elif sys.platform == "win32":
        # Windows paths
        candidates.extend([
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            os.path.expandvars("%LOCALAPPDATA%\\Google\\Chrome\\Application\\chrome.exe"),
            os.path.expandvars("%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe"),
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        ])
    
    return candidates


def _is_chrome_running(host: str, port: int) -> bool:
    """Check if Chrome is running with remote debugging on the given port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _launch_chrome_windows(chrome_path: str, port: int) -> subprocess.Popen:
    """Launch Chrome on Windows via PowerShell with remote debugging."""
    user_data_dir = os.path.expandvars("%TEMP%\\chrome_debug_temp")
    
    powershell_script = f'''
    Start-Process -FilePath "{chrome_path}" -ArgumentList "--remote-debugging-port={port}","--user-data-dir={user_data_dir}" -WindowStyle Hidden
    '''
    
    process = subprocess.Popen(
        ["powershell", "-Command", powershell_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
    )
    return process


def launch_browser(url: Optional[str] = None, headless: bool = False) -> dict:
    """
    Launch Chrome browser with CDP debugging enabled.
    
    Returns dict with connection info including host, port, and ws_url.
    """
    host = get_browser_cdp_host()
    port = get_browser_cdp_port()
    
    # Check if Chrome is already running with remote debugging
    if _is_chrome_running(host, port):
        set_browser_cdp_url(host, port)
        return {
            "status": "already_running",
            "host": host,
            "port": port,
            "url": os.environ.get("BROWSER_CDP_URL"),
        }
    
    # Find Chrome executable
    chrome_path = None
    for candidate in _get_chrome_candidates():
        if sys.platform == "win32":
            if os.path.exists(candidate):
                chrome_path = candidate
                break
        else:
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                chrome_path = candidate
                break
    
    if not chrome_path:
        raise RuntimeError(
            f"Chrome not found. Please install Chrome or Chromium. "
            f"Searched paths: {_get_chrome_candidates()}"
        )
    
    # Launch Chrome based on platform
    if sys.platform == "win32":
        _launch_chrome_windows(chrome_path, port)
    else:
        # macOS/Linux launch
        debug_args = [
            chrome_path,
            f"--remote-debugging-port={port}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        if headless:
            debug_args.append("--headless")
        if url:
            debug_args.append(url)
        
        subprocess.Popen(
            debug_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True
        )
    
    # Wait for Chrome to be ready
    max_attempts = 30
    for i in range(max_attempts):
        if _is_chrome_running(host, port):
            break
        time.sleep(0.5)
    
    # Set the CDP URL environment variable
    set_browser_cdp_url(host, port)
    
    return {
        "status": "launched",
        "host": host,
        "port": port,
        "url": os.environ.get("BROWSER_CDP_URL"),
        "chrome_path": chrome_path,
    }


def get_cdp_info() -> dict:
    """Get current CDP connection info from environment."""
    return {
        "host": get_browser_cdp_host(),
        "port": get_browser_cdp_port(),
        "url": os.environ.get("BROWSER_CDP_URL"),
    }
