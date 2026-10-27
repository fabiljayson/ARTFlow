"""Unit tests for magic-bytes upload validation (EX-6)."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError

from apps.artists.file_validation import MAX_UPLOAD_BYTES, validate_upload

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PDF = b"%PDF-1.7\n" + b"%" + b"\x00" * 32


def _f(content, name="doc"):
    return SimpleUploadedFile(name, content)


def test_valid_png():
    assert validate_upload(_f(PNG, "a.png")) == "image/png"


def test_valid_jpeg():
    assert validate_upload(_f(JPEG, "a.jpg")) == "image/jpeg"


def test_valid_pdf():
    assert validate_upload(_f(PDF, "a.pdf")) == "application/pdf"


def test_rejects_executable():
    with pytest.raises(ValidationError):
        validate_upload(_f(b"MZ\x90\x00" + b"\x00" * 32, "evil.exe"))


def test_rejects_php():
    with pytest.raises(ValidationError):
        validate_upload(_f(b"<?php echo 1; ?>" + b"\x00" * 16, "evil.php"))


def test_rejects_empty():
    with pytest.raises(ValidationError):
        validate_upload(_f(b"", "empty.png"))


def test_rejects_oversized():
    big = SimpleUploadedFile("big.png", b"\x89PNG" + b"\x00" * (MAX_UPLOAD_BYTES + 1))
    with pytest.raises(ValidationError):
        validate_upload(big)


def test_rejects_spoofed_extension():
    # .png extension but executable content
    with pytest.raises(ValidationError):
        validate_upload(_f(b"MZ\x90\x00" + b"\x00" * 32, "fake.png"))
