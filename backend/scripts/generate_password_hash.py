"""
One-time utility (Section 6): run this to generate the bcrypt hash you paste
into .env as AUTH_PASSWORD_HASH. There is no admin UI or DB to do this for you.

Usage:
    cd backend
    python scripts/generate_password_hash.py
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.security import hash_password  # noqa: E402

if __name__ == "__main__":
    pw = getpass.getpass("Enter the admin password to hash: ")
    confirm = getpass.getpass("Confirm password: ")
    if pw != confirm:
        print("Passwords did not match. Aborting.")
        raise SystemExit(1)

    print("\nAUTH_PASSWORD_HASH=" + hash_password(pw))
    print("\nCopy the line above into backend/.env")