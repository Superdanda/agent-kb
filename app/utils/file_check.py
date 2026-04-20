"""File extension and magic number validation utilities."""

from typing import Tuple

ALLOWED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".zip"}
DENIED_EXTENSIONS = {".exe", ".bat", ".cmd", ".ps1", ".sh", ".py", ".jar", ".html", ".svg", ".dll", ".js"}

# Magic bytes signatures
MAGIC_SIGNATURES = {
    b"%PDF": "pdf",
    b"PK": "docx",  # DOCX and ZIP share PK signature
    b"MZ": "exe",
}


def validate_extension(filename: str) -> bool:
    """Validate that the file extension is in the allowed set."""
    import os
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS


def get_magic_type(header_bytes: bytes) -> str:
    """Determine file type from magic bytes in the header.
    
    Returns: "pdf", "docx", "zip", "exe", or "unknown"
    """
    if len(header_bytes) < 2:
        return "unknown"

    # Check PDF
    if header_bytes[:4] == b"%PDF":
        return "pdf"
    
    # Check for PK signature (DOCX or ZIP)
    if header_bytes[:2] == b"PK":
        return "docx"
    
    # Check EXE
    if header_bytes[:2] == b"MZ":
        return "exe"
    
    return "unknown"


def validate_magic_number(file_bytes: bytes) -> Tuple[bool, str]:
    """Validate magic bytes to confirm file type.
    
    Returns: (is_valid, type_str) where is_valid is True if magic bytes
    match an expected type and type_str describes the detected type.
    """
    magic_type = get_magic_type(file_bytes)
    
    if magic_type in ("pdf", "docx", "exe"):
        return True, magic_type
    
    # Unknown type - could be a text file or other acceptable format
    return False, "unknown"
