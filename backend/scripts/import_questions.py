"""Import extracted question data only when explicitly invoked by the operator."""
import argparse
from collections import Counter
import json
from pathlib import Path
import psycopg
from pydantic import ValidationError
from app.db import audit, database
from app.questions import prepare_bank


def main():
    parser=argparse.ArgumentParser(description='Validate/import the extracted Prompt War banks; never starts a round.')
    parser.add_argument('--file',type=Path,default=Path(__file__).resolve().parents[1]/'data'/'question_bank.json')
    parser.add_argument('--organiser-email')
    parser.add_argument('--dry-run',action='store_true',help='Validate and print counts without any database connection')
    args=parser.parse_args()
    try:
        rows=prepare_bank(json.loads(args.file.read_text(encoding='utf-8-sig')))
        print('Validated questions:',dict(Counter(row['kind'] for row in rows)))
        if args.dry_run:
            print('Dry run only. No database connection or import was performed.')
            return
        if not args.organiser_email:
            parser.error('--organiser-email is required for an actual import')
        with database() as conn:
            conn.execute('SELECT pg_advisory_xact_lock(803126)')
            actor=conn.execute("SELECT user_id FROM members WHERE email=%s AND role='organiser' AND active",(args.organiser_email.strip().lower(),)).fetchone()
            if not actor:
                raise ValueError('Bootstrap an approved organiser before importing questions.')
            changed=[]
            for data in rows:
                existing=conn.execute('SELECT id,content_hash FROM question_bank WHERE key=%s',(data['key'],)).fetchone()
                if not existing or existing['content_hash']!=data['content_hash']:
                    changed.append(data)
            kinds=list({data['kind'] for data in changed})
            if kinds:
                if conn.execute("SELECT 1 FROM rounds WHERE kind=ANY(%s) AND status<>'waiting' FOR UPDATE",(kinds,)).fetchone():
                    raise ValueError('Cannot change a bank after its briefing has opened. Identical imports remain safe.')
                if conn.execute('SELECT 1 FROM question_assignments a JOIN question_bank q ON q.id=a.question_id WHERE q.kind=ANY(%s)',(kinds,)).fetchone():
                    raise ValueError('Assigned question banks are locked. This import was rolled back.')
            for data in changed:
                conn.execute("""INSERT INTO question_bank(key,kind,original_round,source_number,source_file,title,task,flawed_output,expected_output,
                    banned_words,banned_word_variants,participant_rules,judge_notes,content_hash)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s)
                    ON CONFLICT(key) DO UPDATE SET kind=excluded.kind,original_round=excluded.original_round,source_number=excluded.source_number,
                    source_file=excluded.source_file,title=excluded.title,task=excluded.task,flawed_output=excluded.flawed_output,
                    expected_output=excluded.expected_output,banned_words=excluded.banned_words,banned_word_variants=excluded.banned_word_variants,
                    participant_rules=excluded.participant_rules,judge_notes=excluded.judge_notes,content_hash=excluded.content_hash,updated_at=now()""",
                    (data['key'],data['kind'],data['original_round'],data['source_number'],data['source_file'],data['title'],data['task'],data['flawed_output'],
                     data['expected_output'],json.dumps(data['banned_words']),json.dumps(data['banned_word_variants']),data['participant_rules'],data['judge_notes'],data['content_hash']))
            audit(conn,actor['user_id'],'import_question_bank',{'file':args.file.name,'validated':len(rows),'changed':len(changed),'unchanged':len(rows)-len(changed)})
        print(f'Imported/updated {len(changed)} questions; {len(rows)-len(changed)} unchanged. No teams were assigned and no round was started.')
    except (OSError,ValueError,ValidationError) as error:
        raise SystemExit('Question import stopped: '+str(error))
    except psycopg.Error as error:
        raise SystemExit('Database import failed ('+type(error).__name__+'). Check migrations and connectivity; no partial import was committed.')


if __name__=='__main__':
    main()
