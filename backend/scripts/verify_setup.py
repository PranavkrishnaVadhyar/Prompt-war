"""Read-only setup checks; never starts services, jobs, or competition actions."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from app.config import settings
from app.questions import prepare_bank

EXPECTED = set('teams members rounds entries submissions evaluations incidents audit_log auth_limits ai_panels ai_runs question_bank question_assignments'.split())
BASELINE = Path(__file__).resolve().parents[1] / '.venv' / 'setup-baseline.json'


def fingerprint(conn):
    result = {}
    tables = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
    for row in tables:
        name = row['tablename']
        query = sql.SQL('SELECT count(*) AS count, md5(coalesce(string_agg(h, chr(10) ORDER BY h), \'\')) AS digest FROM (SELECT md5(row_to_json(t)::text) h FROM {} t) s').format(sql.Identifier('public', name))
        result[name] = dict(conn.execute(query).fetchone())
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--email', required=True)
    args = parser.parse_args()
    config = settings()
    reference = urlsplit(config.supabase_url).hostname.split('.')[0]
    if reference not in config.postgres_url:
        raise RuntimeError('Database and Supabase target references differ')
    response = httpx.get(config.supabase_url.rstrip('/') + '/auth/v1/admin/users',
                        params={'page': 1, 'per_page': 1},
                        headers={'apikey': config.supabase_service_role_key,
                                 'Authorization': 'Bearer ' + config.supabase_service_role_key}, timeout=20)
    if response.status_code != 200:
        raise RuntimeError('Supabase service-role verification failed; HTTP ' + str(response.status_code))
    users = response.json().get('users', [])
    with psycopg.connect(config.postgres_url, row_factory=dict_row, connect_timeout=15) as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        conn.execute("SET LOCAL statement_timeout='60s'")
        for user in users:
            if not conn.execute('SELECT 1 FROM auth.users WHERE id=%s', (user['id'],)).fetchone():
                raise RuntimeError('Auth identity does not match database target')
        print('Supabase service-role authentication and database target verified.')
        public = fingerprint(conn)
        identity = conn.execute('SELECT id, md5(row_to_json(u)::text) AS digest FROM auth.users u WHERE lower(email)=%s', (args.email.lower(),)).fetchone()
        tables = {r['tablename'] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='prompt_war'")}
        if args.baseline:
            if BASELINE.exists():
                raise RuntimeError('Baseline already exists; refusing to overwrite')
            BASELINE.write_text(json.dumps({'public': public, 'identity': dict(identity) if identity else None}, default=str), encoding='utf-8')
            print('Baseline saved privately; public tables:', len(public))
            print('Organiser identity already exists:', bool(identity))
            print('Existing PromptWar tables:', len(tables))
            if 'rounds' in tables:
                print('Existing round states:', conn.execute('SELECT stage,kind,status FROM prompt_war.rounds ORDER BY stage').fetchall())
            return
        baseline = json.loads(BASELINE.read_text(encoding='utf-8'))
        if public != baseline['public']:
            raise RuntimeError('Public table data differs from baseline; investigate concurrent changes')
        if baseline['identity'] and (not identity or str(identity['id']) != baseline['identity']['id'] or identity['digest'] != baseline['identity']['digest']):
            raise RuntimeError('Existing organiser auth identity changed')
        if tables != EXPECTED:
            raise RuntimeError('Expected exactly 13 competition tables')
        restrictions = conn.execute("""SELECT c.relname,c.relrowsecurity,
            has_table_privilege('anon',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS anon_access,
            has_table_privilege('authenticated',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS user_access
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='prompt_war' AND c.relkind='r'""").fetchall()
        if any(not r['relrowsecurity'] or r['anon_access'] or r['user_access'] for r in restrictions):
            raise RuntimeError('Competition table access restrictions failed')
        for role in ('anon', 'authenticated'):
            if conn.execute("SELECT has_schema_privilege(%s,'prompt_war','USAGE') AS allowed", (role,)).fetchone()['allowed']:
                raise RuntimeError('Browser role has schema access')
        constraints = conn.execute("""SELECT conname,contype,convalidated FROM pg_constraint
            WHERE connamespace='prompt_war'::regnamespace""").fetchall()
        if any(not c['convalidated'] for c in constraints):
            raise RuntimeError('Unvalidated competition constraint')
        names = {c['conname'] for c in constraints}
        if not {'submission_assignment_matches_team','direct_submission_has_no_file'} <= names:
            raise RuntimeError('Required submission constraints missing')
        for table in EXPECTED:
            if not conn.execute("SELECT 1 FROM pg_constraint WHERE conrelid=%s::regclass AND contype='p'", ('prompt_war.'+table,)).fetchone():
                raise RuntimeError('Missing primary key')
        rounds = conn.execute('SELECT stage,kind,status FROM prompt_war.rounds ORDER BY stage').fetchall()
        if [(r['stage'],r['kind'],r['status']) for r in rounds] != [(1,'fix','waiting'),(2,'word_ban','waiting'),(3,'recreate','waiting')]:
            raise RuntimeError('Unexpected round mapping or state')
        for table in ('teams','entries','submissions','evaluations','question_assignments','ai_panels','ai_runs'):
            count = conn.execute(sql.SQL('SELECT count(*) AS n FROM {}').format(sql.Identifier('prompt_war', table))).fetchone()['n']
            print(table + ':', count)
            if count:
                raise RuntimeError('Competition records already exist; review before event')
        rows = conn.execute('SELECT key,kind,content_hash,active FROM prompt_war.question_bank').fetchall()
        prepared = prepare_bank(json.loads((Path(__file__).resolve().parents[1]/'data'/'question_bank.json').read_text(encoding='utf-8-sig')))
        if {r['key']:r['content_hash'] for r in rows} != {r['key']:r['content_hash'] for r in prepared} or not all(r['active'] for r in rows):
            raise RuntimeError('Stored bank differs from approved local bank')
        print('Stored question counts:', {kind:sum(r['kind']==kind for r in rows) for kind in ('fix','word_ban','recreate')})
        member = conn.execute("SELECT role,active FROM prompt_war.members WHERE email=%s", (args.email.lower(),)).fetchone()
        if not member or member['role']!='organiser' or not member['active']:
            raise RuntimeError('Organiser is not approved')
        models = [m.strip() for m in config.groq_eval_models.split(',')]
        if len(models)!=3 or len(set(models))!=3 or not all(models) or not config.groq_api_key or not config.openai_api_key or not config.openai_eval_model:
            raise RuntimeError('Provider configuration missing')
        print('13 tables; RLS and browser restrictions verified; validated constraints:', len(constraints))
        print('All stages waiting in the required order; organiser approved; provider configuration present (no provider requests).')
        print('Public table fingerprints unchanged; existing organiser identity preserved.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Connection/configuration errors can contain secrets; never print their details.
        print('Setup verification stopped (' + type(error).__name__ + ').')
        if isinstance(error, RuntimeError):
            print(str(error))
        raise SystemExit(1)
