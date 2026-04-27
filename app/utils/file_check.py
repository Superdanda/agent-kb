"""File extension and magic number validation utilities."""

import os
import unicodedata
from typing import Tuple

ALLOWED_EXTENSIONS = {
    ".md", ".txt", ".pdf", ".docx", ".zip", ".yaml", ".yml", ".json",
    ".jpg", ".jpeg", ".png",
}
DENIED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".ps1", ".sh", ".py", ".jar", ".html",
    ".svg", ".dll", ".js", ".msi", ".com", ".scr", ".vbs", ".wsf",
}
TEXT_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml"}


def normalize_filename(filename: str) -> str:
    """Normalize filenames before extension checks to reduce Unicode spoofing risk."""
    return unicodedata.normalize("NFKC", filename or "")


def validate_extension(filename: str) -> bool:
    """Validate that the file extension is in the allowed set and not denied.

    The check intentionally rejects filenames that change under NFKC normalization
    so full-width suffixes such as ``evil.pdｆ`` cannot bypass extension rules.
    """
    normalized = normalize_filename(filename)
    if normalized != (filename or ""):
        return False

    _, ext = os.path.splitext(normalized.lower())
    if ext in DENIED_EXTENSIONS:
        return False
    return ext in ALLOWED_EXTENSIONS


def is_text_extension(filename: str) -> bool:
    _, ext = os.path.splitext(normalize_filename(filename).lower())
    return ext in TEXT_EXTENSIONS


def _looks_like_utf8_text(header_bytes: bytes) -> bool:
    if b"\x00" in header_bytes:
        return False
    try:
        header_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def get_magic_type(header_bytes: bytes) -> str:
    """Determine file type from magic bytes in the header.

    Returns: "pdf", "zip", "exe", "png", "jpg", "text", or "unknown".
    """
    if len(header_bytes) < 2:
        return "unknown"

    if header_bytes[:4] == b"%PDF":
        return "pdf"

    if header_bytes[:2] == b"PK":
        return "zip"

    if header_bytes[:2] == b"MZ":
        return "exe"

    if header_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"

    if header_bytes[:3] == b"\xff\xd8\xff":
        return "jpg"

    if _looks_like_utf8_text(header_bytes):
        return "text"

    return "unknown"


def validate_magic_number(file_bytes: bytes) -> Tuple[bool, str]:
    """Validate magic bytes to confirm file type.

    Executables are explicitly rejected even if their extension was renamed.
    Text files are accepted when their header is valid UTF-8 and contains no NUL
    bytes, which keeps Markdown/TXT/YAML uploads usable without weakening binary
    file validation.
    """
    magic_type = get_magic_type(file_bytes)

    if magic_type in {"pdf", "zip", "text", "png", "jpg"}:
        return True, magic_type
    if magic_type == "exe":
        return False, "exe"

    return False, "unknown"
