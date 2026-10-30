"""Explicitly approve the first organiser; does not send email or change existing passwords."""
import argparse
from email_validator import validate_email
from app.db import database, audit
from app.supabase import ensure_user


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    email = validate_email(args.email, check_deliverability=False).normalized.lower()
    with database() as conn:
        existing = conn.execute("SELECT role FROM members WHERE email=%s", (email,)).fetchone()
        if existing and existing["role"] != "organiser":
            raise SystemExit("This email already has another Prompt War role. Choose a separate staff email.")
        user_id = ensure_user(email)
        conn.execute("""INSERT INTO members(user_id,email,role) VALUES (%s,%s,'organiser')
            ON CONFLICT(user_id) DO UPDATE SET active=true""", (user_id,email))
        audit(conn,user_id,"bootstrap_organiser",{"email":email})
    print("Organiser approved. Use the existing account password or run scripts.set_password in a private terminal.")


if __name__ == "__main__":
    main()

