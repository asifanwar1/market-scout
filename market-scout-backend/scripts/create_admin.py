"""One-off script to create the first admin account (or promote an existing user).

Users can only be created by an admin through the API, so this is how the very first
admin comes into existence. Run it from the project root with the venv active:

    python -m scripts.create_admin --email you@example.com --password "Str0ng!Pass" --name "Your Name"

If the email already exists, that user is promoted to admin and reactivated instead of
creating a duplicate account.
"""
import argparse
import sys

from app.core.security import hash_password, validate_password_strength
from app.database import SessionLocal
from app.features.users.models import User, UserRole


def create_or_promote_admin(email: str, password: str | None, full_name: str | None) -> None:
    email = email.strip().lower()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.role = UserRole.ADMIN.value
            user.is_active = True
            if password:
                user.hashed_password = hash_password(validate_password_strength(password))
            user.token_version += 1
            db.commit()
            print(f"Promoted existing user {email} to admin.")
            return

        if not password or not full_name:
            print("No existing user with that email; --password and --name are required to create one.", file=sys.stderr)
            sys.exit(1)

        user = User(
            email=email,
            full_name=full_name,
            role=UserRole.ADMIN.value,
            hashed_password=hash_password(validate_password_strength(password)),
        )
        db.add(user)
        db.commit()
        print(f"Created new admin user {email}.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", help="Required when creating a new user")
    parser.add_argument("--name", dest="full_name", help="Required when creating a new user")
    args = parser.parse_args()
    create_or_promote_admin(args.email, args.password, args.full_name)
