from app.core.exceptions import FileAccessError
from app.utils.error_handler import build_error_information


def test_application_error_uses_user_message():
    exc = FileAccessError("Friendly message for the user.")
    info = build_error_information(exc)
    assert info.user_message == "Friendly message for the user."
    assert info.code == "ETC-FILE-ACCESS"
    assert info.error_id.startswith("ETC-")


def test_unexpected_exception_gets_generic_friendly_message():
    try:
        raise ValueError("some internal detail that should not reach the user directly")
    except ValueError as exc:
        info = build_error_information(exc)

    assert "unexpected error" in info.user_message.lower()
    assert "some internal detail" not in info.user_message
    assert "some internal detail" in info.technical_detail


def test_error_id_is_unique_across_calls():
    exc1 = FileAccessError("a")
    exc2 = FileAccessError("b")
    info1 = build_error_information(exc1)
    info2 = build_error_information(exc2)
    assert info1.error_id != info2.error_id
