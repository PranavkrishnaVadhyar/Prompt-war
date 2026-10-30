"""Organiser CSV enrolment; plaintext passwords are never stored or returned."""
import csv
import io
from collections import Counter

import psycopg
from email_validator import validate_email, EmailNotValidError
from fastapi import HTTPException

from .db import database, audit
from . import supabase


def parse_csv(text, shared_password, email_column, team_column):
    if len(text.encode('utf-8')) > 65536:
        raise HTTPException(422, 'CSV must be at most 64 KB.')
    try:
        reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')), strict=True)
        headers = [h.strip().lower() for h in (reader.fieldnames or [])]
        email_column, team_column = email_column.strip().lower(), team_column.strip().lower()
        if not headers or len(set(headers)) != len(headers) or not {email_column, team_column} <= set(headers) or email_column == team_column:
            raise HTTPException(422, 'Specify two different existing column headers for email and team name. Duplicate headers are not supported.')
        reader.fieldnames = headers
        rows, passwords = [], set()
        for number, raw in enumerate(reader, 2):
            if len(rows) >= 44:
                raise HTTPException(422, 'Import at most 44 participants at a time.')
            if None in raw or any(v is None for v in raw.values()):
                raise HTTPException(422, f'CSV row {number} has the wrong number of columns.')
            try:
                email = validate_email(raw[email_column].strip(), check_deliverability=False).normalized.lower()
            except EmailNotValidError:
                raise HTTPException(422, f'CSV row {number} has an invalid email.')
            team = raw[team_column].strip()
            if not 2 <= len(team) <= 100:
                raise HTTPException(422, f'CSV row {number} needs a team_name of 2–100 characters.')
            if 'password' in raw:
                passwords.add(raw['password'])
            rows.append({'row': number, 'email': email, 'team_name': team})
    except csv.Error:
        raise HTTPException(422, 'Malformed CSV. Check quoting and column separators.')
    if not rows:
        raise HTTPException(422, 'CSV contains no participants.')
    if len({r['email'] for r in rows}) != len(rows):
        raise HTTPException(422, 'Duplicate emails in CSV. Each participant must appear once.')
    if any(n > 2 for n in Counter(r['team_name'] for r in rows).values()):
        raise HTTPException(422, 'Each team may have at most two participants.')
    if passwords and (len(passwords) != 1 or '' in passwords):
        raise HTTPException(422, 'Every CSV password must be the same nonempty value.')
    password = next(iter(passwords)) if passwords else shared_password
    if passwords and shared_password and password != shared_password:
        raise HTTPException(422, 'CSV passwords and the shared password field must match.')
    if not 12 <= len(password) <= 200 or len(password.encode('utf-8')) > 72:
        raise HTTPException(422, 'Shared password must be 12–200 characters and at most 72 UTF-8 bytes.')
    return rows, password


def plan(conn, rows):
    first = conn.execute('SELECT id,status FROM rounds WHERE stage=1 FOR UPDATE').fetchone()
    if not first or first['status'] != 'waiting':
        raise HTTPException(409, 'Enrolment closes at the first briefing.')
    teams = {r['name']: r for r in conn.execute('SELECT t.id,t.name,count(m.user_id) AS size FROM teams t LEFT JOIN members m ON m.team_id=t.id GROUP BY t.id')}
    sizes = {name: t['size'] for name, t in teams.items()}
    result = []
    for row in rows:
        item = dict(row)
        identity = conn.execute('SELECT id FROM auth.users WHERE lower(email)=%s', (row['email'],)).fetchone()
        member = conn.execute('SELECT m.role,m.active,t.name FROM members m LEFT JOIN teams t ON t.id=m.team_id WHERE m.email=%s OR m.user_id=%s', (row['email'], identity['id'] if identity else None)).fetchone()
        item['identity_id'] = str(identity['id']) if identity else None
        if member:
            item['status'] = 'already_enrolled' if member['role']=='participant' and member['active'] and member['name']==row['team_name'] else 'conflict'
        else:
            item['status'] = 'ready'
            if identity:
                item['message'] = 'Existing account will be enrolled; its current password is preserved.'
            sizes[row['team_name']] = sizes.get(row['team_name'], 0) + 1
            if sizes[row['team_name']] > 2:
                raise HTTPException(409, 'Import would exceed two members in a team.')
        result.append(item)
    if len(sizes) > 22:
        raise HTTPException(409, 'Import would exceed the 22-team limit.')
    return first, result


def run(text, password, preview, actor, email_column, team_column):
    rows, password = parse_csv(text, password, email_column, team_column)
    # Preflight all local constraints before any Auth mutation.
    with database() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(803126)')
        _, planned = plan(conn, rows)
    if preview:
        return {'preview': True, 'rows': [{k:v for k,v in r.items() if k!='identity_id'} for r in planned]}
    results = []
    for row in rows:
        try:
            # Commit each participant separately: successful rows survive a later failure.
            with database() as conn:
                conn.execute('SELECT pg_advisory_xact_lock(803126)')
                first, current = plan(conn, [row])
                item = current[0]
                if item['status'] != 'ready':
                    results.append({k:v for k,v in item.items() if k!='identity_id'})
                    continue
                user_id = item['identity_id'] or supabase.call('POST', '/auth/v1/admin/users', {'email': row['email'], 'password': password, 'email_confirm': True}, admin=True)['id']
                # Never overwrite an existing membership, even if its email has changed.
                if conn.execute('SELECT 1 FROM members WHERE user_id=%s', (user_id,)).fetchone():
                    raise HTTPException(409, 'Identity already has a PromptWar membership.')
                team = conn.execute("INSERT INTO teams(name,workstation) VALUES (%s,'') ON CONFLICT(name) DO UPDATE SET name=excluded.name RETURNING id", (row['team_name'],)).fetchone()
                conn.execute("INSERT INTO members(user_id,email,role,team_id) VALUES (%s,%s,'participant',%s)", (user_id,row['email'],team['id']))
                conn.execute('INSERT INTO entries(round_id,team_id) VALUES (%s,%s) ON CONFLICT DO NOTHING', (first['id'],team['id']))
                audit(conn, actor, 'import_participant', {'email':row['email'],'team_id':str(team['id']),'existing_identity_reused':bool(item['identity_id']),'existing_password_replaced':False})
            results.append({**row, 'status':'imported', 'message':'Existing password preserved.' if item['identity_id'] else 'Shared password set for new account.'})
        except (HTTPException, psycopg.Error, KeyError):
            # Auth is external to PostgreSQL: never claim that a failed row rolled it back.
            results.append({**row, 'status':'failed_check_account', 'message':'Not enrolled. Auth creation may have succeeded; inspect the account before retrying.'})
            break
    completed = len(results)
    results.extend({**r, 'status':'not_attempted'} for r in rows[completed:])
    return {'preview':False,'rows':results}
