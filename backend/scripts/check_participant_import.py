"""Read-only diagnosis of a participant import; emits no credentials."""
import argparse
from app.db import database


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--email', required=True)
    args = parser.parse_args()
    with database() as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        identity = conn.execute('SELECT 1 FROM auth.users WHERE lower(email)=%s', (args.email.lower(),)).fetchone()
        print('Supabase Auth identity exists:', bool(identity))
        rows = conn.execute('SELECT m.email,m.role,m.active,t.name AS team_name FROM members m LEFT JOIN teams t ON t.id=m.team_id WHERE m.email=%s', (args.email.lower(),)).fetchall()
        print('PromptWar membership:', rows)
        print('PromptWar teams:', conn.execute('SELECT name FROM teams ORDER BY name').fetchall())
        print('Stage 1:', conn.execute('SELECT status FROM rounds WHERE stage=1').fetchone())
        print('Import audit records:', conn.execute("SELECT count(*) AS count FROM audit_log WHERE action='import_participant' AND details->>'email'=%s", (args.email.lower(),)).fetchone())


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Read-only check failed (' + type(error).__name__ + '); sensitive details withheld.')
        raise SystemExit(1)
