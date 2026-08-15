import os
import stat
import sys

import pytest

from app.core.exceptions import (
    FileNotFoundInAppError,
    FileTooLargeError,
    PermissionDeniedError,
    UnsupportedFileTypeError,
)
from app.io.file_reader import read_text_file


def test_missing_file_raises_friendly_error(tmp_path):
    missing = tmp_path / "does_not_exist.txt"
    with pytest.raises(FileNotFoundInAppError):
        read_text_file(missing)


def test_reads_utf8_file(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("hello\nworld\n", encoding="utf-8")
    result = read_text_file(path)
    assert result.text == "hello\nworld\n"
    assert result.metadata.encoding in ("utf-8", "ascii")


def test_reads_utf8_bom_file(tmp_path):
    path = tmp_path / "bom.txt"
    path.write_bytes(b"\xef\xbb\xbfhello\n")
    result = read_text_file(path)
    assert "hello" in result.text
    assert "utf-8" in result.metadata.encoding.lower()


def test_reads_utf16_file(tmp_path):
    path = tmp_path / "u16.txt"
    path.write_bytes("hello world".encode("utf-16"))
    result = read_text_file(path)
    assert "hello world" in result.text


def test_unsupported_binary_extension_rejected(tmp_path):
    path = tmp_path / "image.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(50))
    with pytest.raises(UnsupportedFileTypeError):
        read_text_file(path)


def test_binary_content_detected_even_with_text_extension(tmp_path):
    path = tmp_path / "sneaky.txt"
    path.write_bytes(b"hello\x00world")
    with pytest.raises(UnsupportedFileTypeError):
        read_text_file(path)


def test_huge_file_requires_confirmation(tmp_path):
    path = tmp_path / "big.txt"
    path.write_text("x" * 1000, encoding="utf-8")
    with pytest.raises(FileTooLargeError):
        read_text_file(path, huge_file_threshold=100)
    # confirmed: should succeed
    result = read_text_file(path, huge_file_threshold=100, huge_file_confirmed=True)
    assert len(result.text) == 1000


def test_empty_file_reads_as_empty_string(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")
    result = read_text_file(path)
    assert result.text == ""


@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX permission model only")
def test_permission_denied_raises_friendly_error(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("Cannot simulate permission denial while running as root")
    path = tmp_path / "locked.txt"
    path.write_text("secret", encoding="utf-8")
    path.chmod(0)
    try:
        with pytest.raises(PermissionDeniedError):
            read_text_file(path)
    finally:
        path.chmod(stat.S_IRWXU)
