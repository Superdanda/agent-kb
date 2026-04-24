import stat
import zipfile
from pathlib import Path

from app.utils.zip_check import validate_zip_safety


def _write_zip(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return path


def test_skill_zip_with_manifest_and_skill_md_is_allowed(tmp_path):
    zip_path = _write_zip(
        tmp_path / "skill.zip",
        {
            "SKILL.md": b"# Contract Review",
            "skill.yaml": b"slug: contract-review\nname: Contract\nversion: 1.0.0\n",
        },
    )

    is_safe, message = validate_zip_safety(str(zip_path))

    assert is_safe, message


def test_zip_rejects_path_traversal(tmp_path):
    zip_path = _write_zip(tmp_path / "bad.zip", {"../evil.txt": b"pwn"})

    is_safe, message = validate_zip_safety(str(zip_path))

    assert not is_safe
    assert "Path traversal" in message


def test_zip_rejects_nested_archives(tmp_path):
    zip_path = _write_zip(tmp_path / "bad.zip", {"nested.zip": b"PK\x03\x04"})

    is_safe, message = validate_zip_safety(str(zip_path))

    assert not is_safe
    assert "Nested archive" in message


def test_zip_rejects_executable_members(tmp_path):
    zip_path = _write_zip(tmp_path / "bad.zip", {"run.sh": b"#!/bin/sh\n"})

    is_safe, message = validate_zip_safety(str(zip_path))

    assert not is_safe
    assert "extension" in message.lower()


def test_zip_rejects_unicode_confusable_filename(tmp_path):
    zip_path = _write_zip(tmp_path / "bad.zip", {"evil.pdｆ": b"%PDF-1.7"})

    is_safe, message = validate_zip_safety(str(zip_path))

    assert not is_safe
    assert "Unicode" in message


def test_zip_rejects_symlink_entries(tmp_path):
    zip_path = tmp_path / "symlink.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        info = zipfile.ZipInfo("link.md")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(info, "target.md")

    is_safe, message = validate_zip_safety(str(zip_path))

    assert not is_safe
    assert "Symbolic links" in message
