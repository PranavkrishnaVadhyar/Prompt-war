"""Explicitly enrol an existing Auth identity, without changing any passwords."""
import argparse
from app.db import database, audit
from app.participant_import import plan
from email_validator import validate_email


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--email', required=True)
    parser.add_argument('--team', required=True)
    parser.add_argument('--organiser-email', required=True)
    args = parser.parse_args()
    email = validate_email(args.email, check_deliverability=False).normalized.lower()
    team_name = args.team.strip()
    if not 2 <= len(team_name) <= 100:
        raise SystemExit('Team name must contain 2–100 characters.')
    with database() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(803126)')
        actor = conn.execute("SELECT user_id FROM members WHERE email=%s AND role='organiser' AND active", (args.organiser_email.lower(),)).fetchone()
        if not actor:
            raise SystemExit('Approved organiser required.')
        first, rows = plan(conn, [{'row':1,'email':email,'team_name':team_name}])
        row = rows[0]
        if row['status']=='already_enrolled':
            print('Already enrolled; no changes made.')
            return
        if row['status']!='ready' or not row['identity_id']:
            raise SystemExit('Existing Auth identity with no conflicting membership required.')
        team = conn.execute("INSERT INTO teams(name,workstation) VALUES (%s,'') ON CONFLICT(name) DO UPDATE SET name=excluded.name RETURNING id", (team_name,)).fetchone()
        conn.execute("INSERT INTO members(user_id,email,role,team_id) VALUES (%s,%s,'participant',%s)", (row['identity_id'],email,team['id']))
        conn.execute('INSERT INTO entries(round_id,team_id) VALUES (%s,%s) ON CONFLICT DO NOTHING', (first['id'],team['id']))
        audit(conn,actor['user_id'],'import_participant',{'email':email,'team_id':str(team['id']),'existing_identity_reused':True,'existing_password_replaced':False})
    print('Team and participant membership saved; stage-1 entry added. Password unchanged.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Enrolment failed ('+type(error).__name__+'); sensitive details withheld.')
        raise SystemExit(1)
