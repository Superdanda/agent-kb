"""文件安全审查工具.

提供上传文件的安全检查功能:
- 文件扩展名校验
- Magic bytes 校验
- ZIP 包结构与内容校验
- 路径遍历攻击防护
"""

import zipfile
import hashlib
import re
from pathlib import Path
from typing import Tuple, List, Optional

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".zip"}
# 拒绝的文件扩展名（高危）
DENIED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".ps1", ".sh", ".py", ".jar",
    ".html", ".svg", ".dll", ".js", ".jsp", ".asp", ".aspx",
    ".php", ".cgi", ".pl", ".rb", ".go", ".rs", ".msi",
}

# Magic bytes 签名
MAGIC_SIGNATURES = {
    b"%PDF": "pdf",
    b"PK\x03\x04": "zip",
    b"PK\x05\x06": "zip",
    b"MZ": "exe",
    b"\x7fELF": "elf",
    b"\xca\xfe\xba\xbe": "macho",
}

# 危险文件内容模式（用于文本文件扫描）
DANGEROUS_PATTERNS = [
    re.compile(rb"<script[^>]*>", re.I),
    re.compile(rb"javascript:", re.I),
    re.compile(rb"on\w+\s*=", re.I),  # onclick, onerror, etc.
    re.compile(rb"<\?php", re.I),
    re.compile(rb"<%", re.I),  # ASP/JSP style
    re.compile(rb"import\s+os", re.I),
    re.compile(rb"import\s+subprocess", re.I),
    re.compile(rb"os\.system", re.I),
    re.compile(rb"subprocess\.", re.I),
    re.compile(rb"eval\s*\(", re.I),
    re.compile(rb"exec\s*\(", re.I),
]

MAX_FILENAME_LENGTH = 255
MAX_CONTENT_SCAN_SIZE = 64 * 1024  # 64KB for content pattern scan


class SecurityCheckResult:
    """安全检查结果."""

    def __init__(
        self,
        is_safe: bool,
        message: str,
        file_type: Optional[str] = None,
        sha256: Optional[str] = None,
        threats: Optional[List[str]] = None,
    ):
        self.is_safe = is_safe
        self.message = message
        self.file_type = file_type
        self.sha256 = sha256
        self.threats = threats or []

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "message": self.message,
            "file_type": self.file_type,
            "sha256": self.sha256,
            "threats": self.threats,
        }


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除危险字符."""
    filename = filename.replace("\\", "/")
    filename = Path(filename).name
    filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)
    if len(filename) > MAX_FILENAME_LENGTH:
        name, ext = Path(filename).stem, Path(filename).suffix
        filename = name[: MAX_FILENAME_LENGTH - len(ext)] + ext
    return filename


def validate_extension(filename: str) -> Tuple[bool, str]:
    """校验文件扩展名.

    Returns:
        (is_allowed, reason)
    """
    import os

    name, ext = os.path.splitext(filename.lower())
    if not ext:
        return False, "No file extension"

    if ext in DENIED_EXTENSIONS:
        return False, f"Extension '{ext}' is not allowed (high-risk file type)"

    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Extension '{ext}' is not in the allowed list"

    return True, "Extension is allowed"


def get_magic_type(header_bytes: bytes) -> str:
    """从文件头部的 Magic bytes 判断文件类型.

    Returns:
        "pdf", "zip", "exe", "elf", "macho", or "unknown"
    """
    if len(header_bytes) < 4:
        return "unknown"

    for magic, ftype in MAGIC_SIGNATURES.items():
        if header_bytes[: len(magic)] == magic:
            return ftype

    return "unknown"


def validate_magic_number(file_bytes: bytes) -> Tuple[bool, str, str]:
    """校验 Magic bytes 与扩展名是否一致.

    Returns:
        (is_valid, detected_type, reason)
    """
    magic_type = get_magic_type(file_bytes)
    return True, magic_type, f"Detected type: {magic_type}"


def compute_sha256(file_bytes: bytes) -> str:
    """计算文件 SHA256 哈希."""
    return hashlib.sha256(file_bytes).hexdigest()


def scan_content_patterns(file_bytes: bytes) -> List[str]:
    """扫描文件内容中的危险模式.

    Returns:
        List of detected threat descriptions
    """
    threats: List[str] = []
    scan_bytes = file_bytes[:MAX_CONTENT_SCAN_SIZE]

    for pattern in DANGEROUS_PATTERNS:
        matches = pattern.findall(scan_bytes)
        if matches:
            threats.append(f"Dangerous pattern detected: {pattern.pattern.decode()}")

    return threats


def validate_file_bytes(
    filename: str,
    file_bytes: bytes,
    scan_content: bool = True,
) -> SecurityCheckResult:
    """对文件字节进行完整安全检查.

    Args:
        filename: 原文件名
        file_bytes: 文件内容
        scan_content: 是否扫描内容危险模式

    Returns:
        SecurityCheckResult
    """
    sha256 = compute_sha256(file_bytes)

    # 1. 扩展名校验
    ext_ok, ext_reason = validate_extension(filename)
    if not ext_ok:
        return SecurityCheckResult(
            is_safe=False,
            message=ext_reason,
            file_type=None,
            sha256=sha256,
            threats=["Invalid extension"],
        )

    # 2. Magic bytes 校验
    magic_ok, magic_type, magic_reason = validate_magic_number(file_bytes)

    # 3. 扩展名与 Magic 类型一致性检查
    import os

    ext = os.path.splitext(filename.lower())[1]
    expected_types = {
        ".pdf": ["pdf"],
        ".docx": ["zip"],
        ".zip": ["zip"],
        ".txt": ["unknown"],
        ".md": ["unknown"],
    }

    if ext in expected_types:
        allowed = expected_types[ext]
        if magic_type not in allowed and magic_type != "unknown":
            return SecurityCheckResult(
                is_safe=False,
                message=f"File content ({magic_type}) does not match extension ({ext})",
                file_type=magic_type,
                sha256=sha256,
                threats=["Type mismatch"],
            )

    # 4. 内容危险模式扫描（仅文本类型）
    threats: List[str] = []
    if scan_content and ext in {".txt", ".md"}:
        content_threats = scan_content_patterns(file_bytes)
        if content_threats:
            return SecurityCheckResult(
                is_safe=False,
                message="Dangerous content patterns detected",
                file_type=magic_type,
                sha256=sha256,
                threats=content_threats,
            )

    return SecurityCheckResult(
        is_safe=True,
        message="File passed security checks",
        file_type=magic_type,
        sha256=sha256,
        threats=[],
    )


def validate_zip_safety(
    zip_bytes: bytes,
    max_files: int = 100,
    max_total_size_mb: int = 50,
) -> SecurityCheckResult:
    """验证 ZIP 文件的安全性.

    Args:
        zip_bytes: ZIP 文件内容
        max_files: 最大文件数量
        max_total_size_mb: 最大解压后总大小（MB）

    Returns:
        SecurityCheckResult
    """
    import io

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            # 检查加密
            for info in zf.infolist():
                if info.flag_bits & 0x1:
                    return SecurityCheckResult(
                        is_safe=False,
                        message="Encrypted ZIP files are not allowed",
                        file_type="zip",
                        threats=["Encrypted archive"],
                    )

            file_count = 0
            total_size = 0
            unsafe_files: List[str] = []

            for info in zf.infolist():
                file_count += 1
                if file_count > max_files:
                    return SecurityCheckResult(
                        is_safe=False,
                        message=f"ZIP contains more than {max_files} files",
                        file_type="zip",
                        threats=[f"Excessive files ({file_count})"],
                    )

                total_size += info.file_size
                max_bytes = max_total_size_mb * 1024 * 1024
                if total_size > max_bytes:
                    return SecurityCheckResult(
                        is_safe=False,
                        message=f"ZIP total uncompressed size exceeds {max_total_size_mb}MB",
                        file_type="zip",
                        threats=["Excessive uncompressed size"],
                    )

                # 检查文件名安全性（路径遍历）
                safe_name = info.filename.replace("\\", "/")
                if ".." in safe_name or safe_name.startswith("/"):
                    return SecurityCheckResult(
                        is_safe=False,
                        message=f"Path traversal detected in: {info.filename}",
                        file_type="zip",
                        threats=["Path traversal attack"],
                    )

                # 检查每个条目的扩展名
                basename = Path(safe_name).name
                if basename and basename != info.filename:
                    ext_ok, _ = validate_extension(basename)
                    if not ext_ok:
                        unsafe_files.append(basename)

            if unsafe_files:
                return SecurityCheckResult(
                    is_safe=False,
                    message=f"ZIP contains unsafe files: {', '.join(unsafe_files[:5])}",
                    file_type="zip",
                    threats=[f"Unsafe files: {', '.join(unsafe_files[:5])}"],
                )

            sha256 = compute_sha256(zip_bytes)
            return SecurityCheckResult(
                is_safe=True,
                message="ZIP file passed security checks",
                file_type="zip",
                sha256=sha256,
                threats=[],
            )

    except zipfile.BadZipFile:
        return SecurityCheckResult(
            is_safe=False,
            message="Invalid ZIP file format",
            file_type="unknown",
            threats=["Malformed archive"],
        )
    except Exception as e:
        return SecurityCheckResult(
            is_safe=False,
            message=f"Error reading ZIP file: {str(e)}",
            file_type="unknown",
            threats=[f"Processing error: {str(e)}"],
        )
