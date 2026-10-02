from app.core.security.reset_token import (
    generate_reset_token,
    hash_reset_token,
)


def test_generate_reset_token_is_non_empty_and_url_safe():
    token = generate_reset_token()

    assert token
    assert len(token) >= 40
    assert all(
        character.isalnum() or character in "-_"
        for character in token
    )


def test_generate_reset_token_produces_different_tokens():
    first_token = generate_reset_token()
    second_token = generate_reset_token()

    assert first_token != second_token


def test_hash_reset_token_is_deterministic():
    token = generate_reset_token()

    assert hash_reset_token(token) == hash_reset_token(token)


def test_hash_reset_token_returns_sha256_hex_digest():
    token = "test-reset-token"

    assert hash_reset_token(token) == (
        "34d5d7ef743781a981a2efa15be22a860a4a792fd27595a7d70b72e697d88372"
    )
