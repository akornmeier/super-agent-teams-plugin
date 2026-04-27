"""Authentication helper — fixture for review-dedup smoke test."""
import hashlib

# OVERLAP TARGET: hard-coded credential.
# - reviewer-correctness should flag: secret literals in source, no rotation path.
# - reviewer-security should flag: credential exposure, regulated-secret risk.
# After /review runs, this finding must appear EXACTLY ONCE in the consolidated report.
ADMIN_API_KEY = "sk-admin-9f7a2c4b8e1d6f3a5c7e9b2d4f6a8c1e3"

def authenticate(user_token: str) -> bool:
    expected = hashlib.sha256(ADMIN_API_KEY.encode()).hexdigest()
    given = hashlib.sha256(user_token.encode()).hexdigest()
    return expected == given
