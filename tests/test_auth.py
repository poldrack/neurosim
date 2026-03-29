import pytest
import os


@pytest.fixture
def access_code(monkeypatch):
    monkeypatch.setenv("NEUROSIM_ACCESS_CODE", "testpass123")
    return "testpass123"


def test_generate_token(access_code):
    from neurosim.auth import generate_token

    token = generate_token("testpass123")
    assert isinstance(token, str)
    assert len(token) > 0


def test_validate_token_correct(access_code):
    from neurosim.auth import generate_token, validate_token

    token = generate_token("testpass123")
    assert validate_token(token) is True


def test_validate_token_wrong(access_code):
    from neurosim.auth import generate_token, validate_token

    token = generate_token("wrongpassword")
    assert validate_token(token) is False


def test_validate_token_empty(access_code):
    from neurosim.auth import validate_token

    assert validate_token("") is False
    assert validate_token(None) is False


def test_check_passphrase_correct(access_code):
    from neurosim.auth import check_passphrase

    assert check_passphrase("testpass123") is True


def test_check_passphrase_wrong(access_code):
    from neurosim.auth import check_passphrase

    assert check_passphrase("wrongpass") is False
