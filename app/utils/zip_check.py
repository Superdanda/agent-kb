"""ZIP file validation utilities for security checks."""

import posixpath
import stat
import unicodedata
import zipfile
from pathlib import Path
from typing import List, Tuple

from app.utils.file_check import validate_extension

NESTED_ARCHIVE_EXTENSIONS = {".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".bz2", ".xz"}


def _normalize_zip_name(filename: str) -> str:
    return filename.replace("\\", "/")


def _is_path_traversal(filename: str) -> bool:
    safe_name = _normalize_zip_name(filename)
    normalized = posixpath.normpath(safe_name)
    return (
        safe_name.startswith("/")
        or normalized == ".."
        or normalized.startswith("../")
        or "/../" in f"/{normalized}/"
    )


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0o170000
    return stat.S_ISLNK(mode)


def _has_unicode_spoofing(filename: str) -> bool:
    return unicodedata.normalize("NFKC", filename) != filename


def _extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_zip_safety(
    zip_path: str,
    max_files: int = 100,
    max_total_size_mb: int = 50,
    max_single_file_size_mb: int = 10,
    reject_nested_archives: bool = True,
) -> Tuple[bool, str]:
    """Validate that a ZIP file is safe to extract.

    Checks:
    - Valid ZIP archive
    - Number of files and total/single-file uncompressed size limits
    - No encrypted files
    - No path traversal
    - No symbolic links
    - No Unicode-confusable filenames
    - No denied or unknown file extensions
    - No nested archives by default
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            file_count = 0
            total_size = 0
            max_total_bytes = max_total_size_mb * 1024 * 1024
            max_single_bytes = max_single_file_size_mb * 1024 * 1024

            for info in zf.infolist():
                if info.is_dir():
                    continue

                if info.flag_bits & 0x1:
                    return False, "Encrypted ZIP files are not allowed"

                if _is_path_traversal(info.filename):
                    return False, f"Path traversal attempt detected: {info.filename}"

                if _is_symlink(info):
                    return False, f"Symbolic links are not allowed: {info.filename}"

                if _has_unicode_spoofing(info.filename):
                    return False, f"Unicode-confusable filenames are not allowed: {info.filename}"

                filename = Path(_normalize_zip_name(info.filename)).name
                if filename and not validate_extension(filename):
                    return False, f"File extension not allowed: {filename}"

                ext = _extension(filename)
                if reject_nested_archives and ext in NESTED_ARCHIVE_EXTENSIONS:
                    return False, f"Nested archive files are not allowed: {filename}"

                file_count += 1
                if file_count > max_files:
                    return False, f"ZIP contains more than {max_files} files"

                if info.file_size > max_single_bytes:
                    return False, f"ZIP member exceeds {max_single_file_size_mb}MB: {filename}"

                total_size += info.file_size
                if total_size > max_total_bytes:
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
    max_total_size_mb: int = 50,
) -> List[str]:
    """Extract a ZIP file and validate contents for security."""
    is_safe, message = validate_zip_safety(zip_path, max_files, max_total_size_mb)
    if not is_safe:
        raise ValueError(message)

    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    extracted_files: List[str] = []

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue

                safe_name = _normalize_zip_name(info.filename)
                filename = Path(safe_name).name
                destination = (output_path / safe_name).resolve()
                if not str(destination).startswith(str(output_path)):
                    raise ValueError(f"Path traversal attempt detected: {info.filename}")

                zf.extract(info, output_path)
                extracted_files.append(filename)

    except zipfile.BadZipFile:
        raise ValueError("Invalid ZIP file format")

    return extracted_files
