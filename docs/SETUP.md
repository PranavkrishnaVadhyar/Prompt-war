# Setup and event operation

## Existing-account team import fixed — 2026-10-31

Existing Supabase identities without a conflicting PromptWar membership are now enrolled into their CSV team instead of skipped. Existing passwords are preserved; the shared import password applies only to newly created identities. Staff/admin membership conflicts remain blocked. Preview/results explain this distinction. Team limits, stage lock and duplicate protection remain unchanged.

At the user's request, ran scripts.enrol_existing_participant for bpranavkrishnavadhyar@gmail.com / ABC using approved organiser bpranavkrishnaofficial@gmail.com. Committed prompt_war.teams, participant membership and stage-1 entry with an audit record. No Auth API mutation, password change, round start, question assignment or evaluation occurred. Supabase Table Editor must select the prompt_war schema, not public. Source changes require backend restart/browser refresh; no application tests were run.

## Admin participant CSV import — current behaviour

Teams & staff now includes Bulk import participants. Select a UTF-8 CSV (maximum 64 KB/44 rows), enter the email and team-name column headers (case-insensitive), and enter one shared password. Alternatively a literal password column may contain the same password on every row. Other registration columns are ignored. Team names are trimmed and case-sensitive; blank teams, duplicate emails, malformed rows and invalid addresses are rejected. Limits remain 22 teams and two members per team; enrolment closes at the first briefing.

POST /api/admin/participants/import is organiser-only and CSRF-protected. Preview validates and reads current state without creating users. The second explicit form submission imports. New identities are created in Supabase Auth with the shared password and confirmed email; participant profiles are stored in prompt_war.members with teams and stage-1 entries. No separate public participants table is created. No login email, question assignment, round start or evaluation is triggered.

Admin/staff passwords and memberships are never changed. All existing Supabase accounts are skipped with existing_account_preserved status, unless already enrolled (reported unchanged); this avoids modifying passwords in shared VYUHAM. The user explicitly required admin passwords stay unchanged; no existing-account reset is exposed by this importer. These skipped accounts do not acquire the shared password. New successfully imported accounts can sign in with their own email and the shared password.

Passwords and source CSV are not stored in the application database, audit log, localStorage or result output. Supabase Auth handles password storage. Validation responses omit submitted input. Preview credentials remain only in the live form/temporary browser memory until import or navigation.

Rows commit separately; import stops at the first operational failure, retaining prior successes and reporting unattempted rows. Auth creation is external to the database transaction: a failed row may leave a new Auth identity, explicitly reported for operator review rather than silently deleting it or resetting its password. Repeated successful imports do not duplicate memberships or teams. No schema migration or new dependency is required.

Source inspection only under the standing no-tests restriction. No CSV import, account creation, server, worker, test or provider call was executed during implementation. Restart backend and hard-refresh browser before use.

## Password sign-in (current behaviour)

PromptWar now uses approved email + password sign-in only. The email-code UI and /api/auth/otp/start and /api/auth/otp/verify routes were removed. Existing Supabase passwords, session cookies, CSRF protection, throttling and role approval remain in place. SMTP is not required for password sign-in. Older OTP instructions below are historical.

No passwords were changed automatically. Existing users can use their Supabase password. For an approved user needing a password, run from backend in an interactive terminal:

```powershell
.\.venv\Scripts\python.exe -m scripts.set_password --email bpranavkrishnaofficial@gmail.com
```

The command confirms the email and prompts twice with hidden input; passwords are never command-line arguments or saved to files. It changes the shared Supabase identity password, so the change also applies to VYUHAM if the identity is used there. It requests no recovery email. Use the same command with the appropriate approved member email after enrolling new participants/staff. New identities otherwise have unknown random passwords. No public self-registration/reset endpoint was added.

Restart the backend and hard-refresh the browser after these source changes. Source inspection only: no tests, server starts or password updates were executed by the agent for this change. Runtime sign-in remains to be checked by the user.

No command, migration, question import or application has been executed during authoring. This guide is for later operator use after authorisation.

## Portable deployment and secrets

Move the entire PromptWar directory. Python commands run from backend/. The backend serves frontend/ only, so its environment and question files remain outside the web root. Do not serve the whole project as static content or open index.html using file://.

backend/.env initially uses the original VYUHAM Supabase project. Verify the intended project before setup. Using the same project shares Auth identities/quotas, but all competition tables are in prompt_war. Change the database URL, Supabase URL and service-role key if a dedicated project is wanted.

Required settings:

- DATABASE_URL: trusted Supabase PostgreSQL schema-owner connection; URL-encode password characters and use sslmode=require. Asyncpg-style URL schemes and ssl query names are normalized for psycopg.
- SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY: server-only Auth verification and provisioning.
- SUPABASE_PUBLISHABLE_KEY: optional Auth API key; service key can be used server-side if omitted.
- FRONTEND_ORIGINS: exact allowed origins, default localhost:8000 and 127.0.0.1:8000.
- COOKIE_SECURE: false locally over HTTP; true for production HTTPS.
- MAX_SUBMISSION_BYTES: defaults to 262144, for canonical UTF-8 text submissions.
- AUTH_IP_LIMIT / AUTH_EMAIL_LIMIT: default 300 / 10 sign-in requests per 15 minutes, accommodating shared venue networks.
- GROQ_API_KEY, GROQ_EVAL_MODELS (three distinct accessible IDs), OPENAI_API_KEY and optional OPENAI_EVAL_MODEL (gpt-4.1-mini default).
- EVALUATION_WORKERS: default 2 submissions simultaneously; each fans out to 4 parallel models. EVALUATION_TIMEOUT: default 60 seconds per request.

No Storage setting or bucket is needed for new submissions. Old STORAGE_BUCKET/MAX_UPLOAD_BYTES/GROQ_MODEL variables are ignored. Never put service-role, database or provider keys in frontend files. Restart server/worker after env changes.

## Authentication

There is no public signup. An organiser approves participant/staff emails. Existing Supabase users keep their passwords; new identities receive unknown random passwords and should sign in using email codes.

Enable Supabase email authentication and configure the appropriate email template to include `{{ .Token }}`. A magic-link-only template is insufficient for this app's code-entry screen. Test SMTP delivery and provider limits. Template/global Auth changes affect other apps sharing this Supabase project; coordinate them.

At check-in, volunteers allocate computers. Phones may be used temporarily to sign into personal email, the designated external LLM and the app, then collected by volunteers. The platform does not implement phone collection or external browser monitoring.

## Install and create tables later

From backend, with Python 3.11 or later:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m scripts.create_tables
python -m scripts.bootstrap_organiser --email YOUR_ORGANISER_EMAIL
```

The setup script applies SQL 001, 002, 003 and 004 in filename order. Existing initial installations must apply the new migrations too. Question tables are empty after setup: SQL deliberately inserts no question rows. All app tables deny direct anon/authenticated browser access; the server uses its privileged DB connection.

No Supabase Storage bucket is created. The non-destructive direct-submission migration leaves any old objects/metadata untouched. There is no need to configure storage policies for the new flow.

## Import questions later

The 33 manually extracted questions are in backend/data/question_bank.json; original Markdown files are in data/sources. Review them first, then run explicitly:

```powershell
python -m scripts.import_questions --dry-run
python -m scripts.import_questions --organiser-email YOUR_ORGANISER_EMAIL
```

Dry-run only validates data and prints counts, without DB access. Actual import uses stable keys/content hashes, requires an approved organiser, logs its action and commits atomically. It assigns no questions and starts no stage. Do not import changed material after briefing/assignment; the script blocks that. Source round labels map by challenge kind: Fix first, Word Ban second, original Round 1/Recreate last.

## Start the app and worker later

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. No npm build is needed. In a second terminal, using the same backend environment:

```powershell
python -m scripts.evaluation_worker
```

The worker only processes explicitly queued jobs. /api/health is process liveness, not a database-readiness check. Default same-origin hosting is recommended. Separate unrelated origins are not supported by default SameSite=Lax cookies; use a same-origin reverse proxy.

## Prepare teams and stages

Enrol up to 22 teams, one or two emails each, and assign workstations. Add judges/volunteers. Team enrolment closes at the first briefing; computer reassignment remains possible with an audit reason.

In Questions & assignments, verify each bank's private preview and active count. In Round control, configure title, optional shared instructions, designated participant LLM, challenge/submission times and preliminary qualifier counts. Actual targets/flawed inputs/bans are drawn from the bank, not manually configured per team in the browser. Settings lock at briefing.

The final has two prize places. Default order/limits are Fix 600 seconds/5 attempts, Word Ban 120/1, Recreate 600/5, each followed by a 300-second submission window.

## Repeat for each stage

1. Brief eligible teams. The question remains hidden.
2. Click Start & assign random questions. One transaction saves each eligible team's random question snapshot and starts common deadlines.
3. Teams work in the external LLM and volunteers monitor rules. Assignment survives refreshes and cannot be rerolled.
4. Challenge expiry opens direct submission. Teams paste exact prompts/answers, select an attempt, save, review and confirm.
5. Submission expiry locks normal entries and opens evaluation/break. Draft-only/absent submissions do not qualify.
6. In Judging, queue all final submissions or a candidate. Each model and human judge gets that candidate's assigned question/target.
7. Review all four marks/reasons and combined suggestion; approve human criteria with comments. Handle outages with explicit cancellation/retry/manual override as documented.
8. Resolve qualification/prize ties through an external surprise task and record its score/evidence.
9. Publish results. Pending panels, active extensions and unapproved final submissions block publication. Top 11 then top 5 advance automatically; the final determines winner/runner-up.
10. Close the stage if desired, then brief the next. No simultaneous active stages.

## Incidents and production

An organiser can pause/resume challenge or submission clocks; volunteers must stop external work during pauses. Individual submission extensions require reasons, keep the same question and invalidate provisional assessments. Disqualifications supersede pending assessment work. Published results have no retraction UI; review before publishing.

Use HTTPS, secure cookies, exact origins and trusted reverse-proxy settings in production. Immediate client-IP throttles can interact with proxies/NAT; test group sign-in. Check DB connection limits, SMTP and provider quotas, backups and fallback procedures. Keep question targets private and sign out of personal LLM accounts after the event.

Apply this architecture before a new event, not midway through a live legacy competition. Historical parsed submissions are retained, but new grading expects saved question-assignment provenance. Complete MANUAL_ACCEPTANCE.md before real use.
