"""Set an approved account's Supabase password using hidden terminal input."""
import argparse
import getpass
import warnings
from email_validator import validate_email
from app.db import database
from app.supabase import call


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--email', required=True)
    args = parser.parse_args()
    email = validate_email(args.email, check_deliverability=False).normalized.lower()
    with database() as conn:
        member = conn.execute('SELECT user_id FROM members WHERE email=%s AND active', (email,)).fetchone()
    if not member:
        raise SystemExit('Email must be an active, approved PromptWar member.')
    print('This sets the shared Supabase account password, including any other app using this identity.')
    print('Existing passwords are replaced only for the selected email. No recovery email is requested.')
    if input('Type the account email to confirm: ').strip().lower() != email:
        raise SystemExit('Cancelled; password unchanged.')
    # Never fall back to echoed input when a secure terminal is unavailable.
    warnings.simplefilter('error', getpass.GetPassWarning)
    password = getpass.getpass('New password (12–200 characters): ')
    if not 12 <= len(password) <= 200 or len(password.encode('utf-8')) > 72:
        raise SystemExit('Use 12–200 characters and at most 72 UTF-8 bytes.')
    if password != getpass.getpass('Confirm new password: '):
        raise SystemExit('Passwords do not match; password unchanged.')
    call('PUT', '/auth/v1/admin/users/' + str(member['user_id']), {'password': password}, admin=True)
    print('Password updated. Sign in to PromptWar with your email and new password.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Password setup failed (' + type(error).__name__ + '); secret details withheld.')
        raise SystemExit(1)
