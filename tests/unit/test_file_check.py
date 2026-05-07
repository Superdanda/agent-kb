from app.utils.file_check import (
    get_magic_type,
    validate_extension,
    validate_magic_number,
)


def test_validate_extension_allows_document_and_skill_manifest_files():
    assert validate_extension("SKILL.md")
    assert validate_extension("skill.yaml")
    assert validate_extension("contract.pdf")
    assert validate_extension("package.zip")


def test_validate_extension_rejects_executables_and_unicode_spoofing():
    assert not validate_extension("evil.exe")
    assert not validate_extension("evil.pdｆ")


def test_magic_number_rejects_renamed_executable():
    is_valid, detected = validate_magic_number(b"MZ" + b"\x00" * 16)

    assert not is_valid
    assert detected == "exe"


def test_magic_number_accepts_text_headers_for_md_txt_yaml():
    is_valid, detected = validate_magic_number(b"# Skill\ncontent: ok\n")

    assert is_valid
    assert detected == "text"


def test_magic_number_detects_zip_and_pdf():
    assert get_magic_type(b"PK\x03\x04payload") == "zip"
    assert get_magic_type(b"%PDF-1.7") == "pdf"
