"""Explicitly transfer PromptWar organiser access without changing Auth accounts."""
import argparse
from email_validator import validate_email
from app.db import database, audit
from app.supabase import ensure_user


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--from-email', required=True)
    parser.add_argument('--to-email', required=True)
    args = parser.parse_args()
    old = validate_email(args.from_email, check_deliverability=False).normalized.lower()
    new = validate_email(args.to_email, check_deliverability=False).normalized.lower()
    if old == new:
        raise RuntimeError('Choose different email addresses.')
    with database() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(803127)')
        previous = conn.execute('SELECT user_id,role FROM members WHERE email=%s FOR UPDATE', (old,)).fetchone()
        target = conn.execute('SELECT user_id,role FROM members WHERE email=%s FOR UPDATE', (new,)).fetchone()
        if not previous or previous['role'] != 'organiser':
            raise RuntimeError('Original organiser not found.')
        if target and target['role'] != 'organiser':
            raise RuntimeError('New email has a different PromptWar role; no roles changed.')
        user_id = ensure_user(new)
        member = conn.execute('SELECT email,role FROM members WHERE user_id=%s FOR UPDATE', (user_id,)).fetchone()
        if member and (member['email'] != new or member['role'] != 'organiser'):
            raise RuntimeError('Identity membership conflict; no memberships changed.')
        conn.execute("INSERT INTO members(user_id,email,role) VALUES (%s,%s,'organiser') ON CONFLICT(user_id) DO UPDATE SET active=true", (user_id,new))
        conn.execute('UPDATE members SET active=false WHERE user_id=%s', (previous['user_id'],))
        audit(conn, user_id, 'change_organiser', {'from_email': old, 'to_email': new, 'previous_user_id': str(previous['user_id'])})
    with database() as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        rows = conn.execute('SELECT email,role,active FROM members WHERE email IN (%s,%s) ORDER BY email', (old,new)).fetchall()
        for row in rows:
            print(row['email'], row['role'], 'active' if row['active'] else 'inactive')
    print('Transfer committed. Auth identities/passwords and historical audit records preserved. No email sent.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Organiser transfer stopped (' + type(error).__name__ + '); sensitive error details withheld.')
        if isinstance(error, RuntimeError):
            print(str(error))
        raise SystemExit(1)
