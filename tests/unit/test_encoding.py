from app.io.encoding import decode_with_detection, detect_encoding
from app.core.enums import EncodingConfidence


def test_detect_utf8_bom():
    data = b"\xef\xbb\xbfhello"
    result = detect_encoding(data)
    assert result.encoding == "utf-8-sig"
    assert result.confidence == EncodingConfidence.HIGH


def test_detect_utf16_bom_le():
    data = "hello".encode("utf-16")
    result = detect_encoding(data)
    assert "utf-16" in result.encoding.lower()


def test_detect_plain_utf8():
    data = "hello world".encode("utf-8")
    result = detect_encoding(data)
    assert result.encoding in ("utf-8", "ascii")  # ascii is valid utf-8 subset


def test_detect_empty_bytes():
    result = detect_encoding(b"")
    assert result.encoding == "utf-8"
    assert result.confidence == EncodingConfidence.HIGH


def test_decode_with_detection_never_raises_on_arbitrary_bytes():
    random_bytes = bytes(range(256))
    text, result = decode_with_detection(random_bytes)
    assert isinstance(text, str)


def test_decode_with_detection_utf8_roundtrip():
    original = "héllo wörld 🚀"
    data = original.encode("utf-8")
    text, result = decode_with_detection(data)
    assert text == original
