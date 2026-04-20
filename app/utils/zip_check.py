"""ZIP file validation utilities for security checks."""

import zipfile
from pathlib import Path
from typing import List, Tuple

from app.utils.file_check import validate_extension


def validate_zip_safety(
    zip_path: str,
    max_files: int = 100,
    max_total_size_mb: int = 50
) -> Tuple[bool, str]:
    """Validate that a ZIP file is safe to extract.
    
    Checks:
    - File is a valid ZIP archive
    - Number of files does not exceed max_files
    - Total uncompressed size does not exceed max_total_size_mb
    - No encrypted files
    
    Returns: (is_safe, message) where is_safe is True if all checks pass
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Check for encryption
            for info in zf.infolist():
                if info.flag_bits & 0x1:
                    return False, "Encrypted ZIP files are not allowed"
            
            # Count files and total size
            file_count = 0
            total_size = 0
            
            for info in zf.infolist():
                file_count += 1
                if file_count > max_files:
                    return False, f"ZIP contains more than {max_files} files"
                
                total_size += info.file_size
                max_bytes = max_total_size_mb * 1024 * 1024
                if total_size > max_bytes:
                    return False, f"ZIP total uncompressed size exceeds {max_total_size_mb}MB"
            
            return True, "ZIP file is safe"
            
    except zipfile.BadZipFile:
        return False, "Invalid ZIP file"
    except Exception as e:
        return False, f"Error reading ZIP file: {str(e)}"


def extract_and_validate(
    zip_path: str,
    output_dir: str,
    max_files: int = 100,
    max_total_size_mb: int = 50
) -> List[str]:
    """Extract a ZIP file and validate contents for security.
    
    Security checks performed:
    - Valid ZIP structure
    - No path traversal attacks (no .. in paths)
    - All files pass extension validation
    - No encrypted files
    - File count and size limits
    
    Returns: List of extracted filenames (basenames only, no paths)
    
    Raises: ValueError if any validation fails
    """
    # First validate the zip
    is_safe, message = validate_zip_safety(zip_path, max_files, max_total_size_mb)
    if not is_safe:
        raise ValueError(message)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    extracted_files: List[str] = []
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for info in zf.infolist():
                # Check for path traversal
                safe_name = info.filename.replace('\\', '/')
                if '..' in safe_name or safe_name.startswith('/'):
                    raise ValueError(f"Path traversal attempt detected: {info.filename}")
                
                # Validate extension
                filename = Path(safe_name).name
                if filename and not validate_extension(filename):
                    raise ValueError(f"File extension not allowed: {filename}")
                
                # Extract file
                zf.extract(info, output_path)
                extracted_files.append(filename)
                
    except zipfile.BadZipFile:
        raise ValueError("Invalid ZIP file format")
    
    return extracted_files
