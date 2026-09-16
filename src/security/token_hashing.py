import hashlib


def hash_token(raw_token: str) -> str:
    """Deterministic SHA-256 hash of a token for safe DB storage/lookup.

    Unlike password hashing, this must be deterministic (same input ->
    same output every time) so we can look the token up by its hash,
    and doesn't need bcrypt's deliberate slowness — the token itself is
    already high-entropy, unlike a human-chosen password.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
