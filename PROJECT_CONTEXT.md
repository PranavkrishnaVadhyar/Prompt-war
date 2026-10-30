# Prompt War project context

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

## Computer tracking disabled — current requirement

The user does not track computers. Removed workstation input/reassignment UI, workstation columns/labels in team lists, question assignments, judging, monitor, participant header and CSV exports. Commented out the allocation API route. Team creation now defaults the retained legacy workstation column to an empty string and rejects nonempty allocations. Existing database values were not modified; no migration is needed. Question assignments remain enabled and unchanged. Source-reviewed only; no tests or servers were executed for this change. Restart the backend and hard-refresh the browser.

## Password sign-in (current behaviour)

PromptWar now uses approved email + password sign-in only. The email-code UI and /api/auth/otp/start and /api/auth/otp/verify routes were removed. Existing Supabase passwords, session cookies, CSRF protection, throttling and role approval remain in place. SMTP is not required for password sign-in. Older OTP instructions below are historical.

No passwords were changed automatically. Existing users can use their Supabase password. For an approved user needing a password, run from backend in an interactive terminal:

```powershell
.\.venv\Scripts\python.exe -m scripts.set_password --email bpranavkrishnaofficial@gmail.com
```

The command confirms the email and prompts twice with hidden input; passwords are never command-line arguments or saved to files. It changes the shared Supabase identity password, so the change also applies to VYUHAM if the identity is used there. It requests no recovery email. Use the same command with the appropriate approved member email after enrolling new participants/staff. New identities otherwise have unknown random passwords. No public self-registration/reset endpoint was added.

Restart the backend and hard-refresh the browser after these source changes. Source inspection only: no tests, server starts or password updates were executed by the agent for this change. Runtime sign-in remains to be checked by the user.

## Organiser changed — 2026-10-30

Current active organiser: bpranavkrishnaofficial@gmail.com. At the user's explicit request, scripts.change_organiser activated this membership and deactivated pranavb.cs26@duk.ac.in in one PromptWar transaction. Both membership states were verified after commit. Supabase identities/passwords and historical import/audit attribution were preserved; no email was sent. Future organiser imports should use the Gmail address. This supersedes the original organiser address in the setup history below. SMTP/default sender restrictions still apply independently of PromptWar membership.


## Setup completed — 2026-10-30 (current status)

This section supersedes earlier pending/setup and authoring-only execution notes below.

- Project: C:\Users\HP\OneDrive\Desktop\Prompt-war. Separate frontend/backend architecture, styling, stage order and human approval rules preserved.
- backend/.venv created with Python 3.14; requirements installed only into this environment. Initial sandbox temp/DNS restrictions were resolved through elevated setup operations.
- User confirmed the existing shared Supabase project. Live service-role authentication succeeded; a returned Auth identity matched auth.users in the configured database. No secret values were printed, logged or committed. backend/.env remains Git-ignored/untracked; configured secrets were not found in frontend files.
- Local HTTP configuration: FRONTEND_ORIGINS=http://127.0.0.1:8000,http://localhost:8000 and COOKIE_SECURE=false. Existing provider credentials and the three previously selected Groq model IDs were preserved. Provider configuration is present, but validity/model entitlement was not tested and no LLM API calls were made.
- Applied 001_prompt_war.sql, 002_evaluation_panels.sql, 003_direct_submissions.sql and 004_question_banks.sql in order through scripts.create_tables. Removed public fallback from migration/backend search paths to isolate unqualified app objects in prompt_war.
- Bootstrapped pranavb.cs26@duk.ac.in as active organiser through the supplied script. No existing identity was found, so Supabase created a confirmed identity with an unknown random password. No login email/code was sent and no existing password or unrelated role was changed. This organiser should use email OTP once delivery is configured.
- Reviewed all extracted question fields/bans against their original source Markdown with no mismatches. Import dry-run passed: 33 questions. Actual import inserted 33; the repeated import changed 0 and reported 33 unchanged. Stored keys/content hashes match the local prepared bank; all are active: 11 fix, 11 word_ban, 11 recreate.
- Read-only verification found exactly 13 competition tables, 69 validated constraints, primary keys on every table, required submission constraints, RLS on every table, and no anon/authenticated table privileges or schema usage.
- All rounds remain waiting: stage 1 fix (source Round 2), stage 2 word_ban (source Round 3), stage 3 recreate (original Round 1 last). No teams, entries, submissions, evaluations, question assignments, AI panels or AI runs exist.
- Before/after row-count/content fingerprints for all 18 public tables matched. Setup made no changes to unrelated public data. Storage objects/buckets were not accessed or changed.
- Added scripts.verify_setup for read-only baseline/readiness checks and scripts.setup_run as a secret-safe wrapper around supplied setup scripts. The private baseline is in ignored backend/.venv/setup-baseline.json. One initial inline wrapper command failed from shell quoting before running a migration; the file-based wrapper resolved it. All database setup operations subsequently succeeded.

This is setup verification, not application testing. No app/frontend server, evaluation worker, test suite, competition action, assignment, model request or login email was executed. End-to-end login/UI/scoring/runtime behaviour remains untested as requested.

Remaining dashboard/operator work: enable/check Supabase email authentication; ensure the OTP email template includes {{ .Token }}; configure SMTP and delivery limits. Shared-project Auth changes must be coordinated with VYUHAM. No Storage bucket is needed. For production later, configure HTTPS/reverse proxy, exact production origins and COOKIE_SECURE=true.

Later startup commands (not executed), from backend/:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a separate terminal also in backend/:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluation_worker
```


## Setup progress — 2026-10-30 (supersedes historical execution status below)

The user authorised virtual-environment creation, dependency installation, migrations, organiser bootstrap, question import and read-only setup verification. Servers, evaluation workers, tests, competition actions, assignments and LLM requests remain prohibited.

Completed:
- Located project at C:\Users\HP\OneDrive\Desktop\Prompt-war; frontend/ and backend/ are present. Inspected all requested documentation and setup scripts. Runtime paths are project-relative; no original-folder/Downloads dependency was found. Static mounting is limited to frontend/.
- Created backend/.venv with installed Python 3.14 and successfully installed backend/requirements.txt using that environment. Sandbox temp-directory/DNS failures were resolved through elevated setup commands. No global dependency installation occurred.
- Confirmed backend/.env is Git-ignored and untracked. Existing secret settings were preserved and never printed. A local scan found none of the configured secret values in frontend files.
- Confirmed local database/Supabase/service-role JWT project references agree, and JWT role is service_role. This is an offline consistency check, not live authentication or proof of the intended project.
- Confirmed the three Groq IDs exactly match the previously documented user selection. Provider keys are populated; validity/access remain unverified. No provider requests occurred.
- User selected production HTTPS; set COOKIE_SECURE=true. Exact FRONTEND_ORIGINS remains pending the deployment URL(s).
- Removed public from SQL migration and backend transaction search paths, limiting unqualified application objects to prompt_war. This prevents fallback to unrelated same-named public objects if competition objects are missing. No SQL has been executed.
- Compared extracted title/task/target/flawed-input/private-note fields and banned words against original Markdown source text: no mismatches. Preserved original question content and stage order.
- Ran backend/.venv/Scripts/python.exe -m scripts.import_questions --dry-run successfully: 11 recreate, 11 fix, 11 word_ban; 33 total. No database connection/import occurred.

Pending required user information: organiser email, confirmation that the existing shared Supabase target is intended (or privately supplied replacements), and exact production HTTPS origin(s).

Migrations, organiser bootstrap and actual question import are NOT completed. Live table/constraint/access checks, stored question counts/idempotency, organiser readiness, waiting round states and absence of assignments/jobs remain unverified. No database data was changed during this setup session. No application tests, servers, workers, rounds, model calls or emails were run/sent.

After the missing details arrive, verify the intended live target and baseline before applying migrations 001–004, bootstrap, import and read-only readiness checks. Supabase email authentication, OTP template containing {{ .Token }}, SMTP/delivery limits and production HTTPS reverse proxy remain operator configuration items; shared-project Auth changes must be coordinated.


## Read first after transfer

This standalone project will be moved and opened in a new chat. Read this file and README.md before continuing. Keep frontend/ separate from backend/ and all paths relative to this project. The earlier VYUHAM-static-only restriction was superseded to create and change this separate PromptWar project.

**Execution restriction:** the user explicitly said not to execute code. Only source reads, file/directory creation, copying and source edits have been performed. No app code, import/extraction script, dependency installation, syntax checker, tests, server, worker, model API call or SQL has been run. No tables, questions or assignments have been created in Supabase by the agent. Obtain later user authorisation before running anything. Existing live DB state is unknown.

## Latest agreed requirements

- FastAPI + Supabase + plain HTML/CSS/JS, maintaining VYUHAM dark/red/pill/serif styling and copied local logos.
- Teams use an external designated LLM. Our app does not generate participant answers or monitor external tabs.
- Participants paste plain text into Prompt and AI answer fields. No file uploads or JSON authoring for participants. The browser automatically serializes fields to JSON for the API.
- Each stage independently completes work → direct submission → evaluation/break → results before the next starts.
- Competition stage 1 is Fix the Output (original Round 2): 22 teams, 10 minutes, max 5 attempts; top 11 advance.
- Stage 2 is Word Ban (original Round 3): 11 teams, 2 minutes, 1 attempt; top 5 advance.
- Stage 3 is Recreate the Target (original Round 1): 5 finalists, 10 minutes, max 5 attempts; winner and runner-up. Original Round 1 must remain last.
- Submission window defaults to 5 minutes after each challenge. Scores reset each stage; no carryover.
- Exactly 3 Groq-hosted models and 1 basic OpenAI model assess each selected final attempt independently in parallel. All four individual marks/reasons, submission evidence and combined suggested score appear before human approval.
- Three supplied question banks have now been extracted locally. The user explicitly requested no question insertion now: create a separate import script instead.
- Admin Start randomly assigns one question to each eligible team. Save assignments so refreshing never rerolls a question, and grade each team against its own assigned target.

## Question data and mapping

The source files were copied verbatim into backend/data/sources/round_1_question_bank.md, round_2_question_bank.md and round_3_question_bank.md. All 33 questions were manually extracted to backend/data/question_bank.json: 11 recreate, 11 fix, 11 word_ban. No extraction/import code was executed. Source numbering is preserved, while the running stage uses challenge kind. The source's old “Round 3 final” and “same task for everyone” statements are superseded by later user instructions.

The extraction preserves titles, descriptions/tasks, exact targets, flawed inputs, Unicode, internal formatting and Word Ban lists. Outer display fences are omitted; inner fences in Fix's Verbose Coder flawed input are preserved. Word Ban engineering hints are stored as private judge_notes, not participant hints. Do not silently rewrite original targets; review source inconsistencies before import if the organiser wants corrections.

Question import is scripts.import_questions, separate from migrations. --dry-run validates without DB connection. Actual import requires an approved organiser email, is transactional/idempotent by stable key and content hash, does not delete missing questions, and refuses changed/new banks after their briefing opens or assignments exist. Unchanged imports are harmless. The script has not been run.

Assignment uses secrets.SystemRandom to shuffle teams and shuffled cycles of active questions matching the round kind. Each question is used once per cycle; another shuffled cycle is used if necessary. With 22 teams/11 questions, every question appears twice; with 11 teams, all are distinct; five finalists get a distinct random subset. This balances frequency, not difficulty.

Admin Start holds lifecycle/round locks, creates assignments and starts deadlines in one transaction. Failed starts roll back both. A unique (round,team) assignment and source snapshot prevent rerolls. Snapshot content is stable through pause, refresh, extension and future bank edits. New submissions store assignment_id with a composite FK matching round/team.

Participants receive only their own assigned question after start; no bank endpoint is available to them. Organisers have Questions & assignments with private bank previews and saved team/computer mappings. Judges receive the assigned question inside each queued submission. All automated checks, model contexts, human approvals and CSV provenance use that question, not the old global round target.

Word Ban source rules include pluralization. Import materializes explicit common English singular/plural forms, including leaf/leaves and money/monies, and publishes/freezes those variants with the question. Match whole words/phrases case-insensitively; no arbitrary stemming or substring matching is claimed. Ban compliance is 0/30 only. Similarity, possible copying and missing literal flawed-input context are advisory flags.

## Architecture

- frontend/index.html loads config.js, panel.js, entry.js and app.js; all assets are local. No frontend build.
- FastAPI serves frontend/ at / and API at /api. Same-origin HTTP locally, HTTPS in production, is the supported default.
- Supabase Auth verifies approved personal-email identities. App roles/team membership come from prompt_war.members, never user metadata.
- HttpOnly SameSite=Lax access/refresh cookies, CSRF header/cookie matching and exact Origin allowlisting protect mutations. No auth token or editor contents in localStorage.
- PostgreSQL schema prompt_war isolates this project from existing public VYUHAM tables. RLS and revocations deny browser-role direct table access; backend uses the trusted database connection.
- New submissions are direct JSONB text, with no Supabase Storage requirement or storage API calls. Migration 003 retains nullable legacy file metadata and old objects without deleting anything.
- backend/.env was copied privately from the old VYUHAM backend and initially targets the same Supabase project. Auth identities are shared if that remains unchanged. No existing passwords/roles are reset when approving users.

## Source responsibilities

- config.py: project-relative environment paths; database URL normalization; origins, limits and provider settings.
- db.py: transaction context, audit writes, server deadline synchronization.
- auth.py / supabase.py: Supabase identity/session/provisioning, approved membership, CSRF and throttling. No Storage helper remains.
- schemas.py: strict request bodies; direct attempts preserve whitespace and reject invalid text/selection.
- submissions.py: direct draft validation, canonical UTF-8 content hash, version limits and insert; locks round then entry.
- questions.py: bank validation, source rules, plural variants, balanced random assignment, per-team/per-submission snapshot context and controlled display.
- competition.py: phase transitions, atomic random assignment at Start, human-score ranking, tie checks and advancement.
- evaluation.py: deterministic checks and criterion validation.
- model_panel.py: three Groq requests, one OpenAI Responses request, schema/score validation and equal-weight aggregation.
- panel_jobs.py: durable queue, frozen per-round model roster, candidate-question snapshots, per-model results, retries, leases and late-result guards.
- main.py: role-protected routes, request-size limits, CSP/security headers and frontend mount.
- frontend/js/entry.js: plain-text attempt editor and capture helpers.
- frontend/js/panel.js: per-model marks/reasons/progress, combined score and history.
- frontend/js/app.js: role screens, entry memory, confirmation, questions/admin controls, judging, monitoring, exports and polling.

## Database and migrations

13 tables, all in prompt_war: teams, members, rounds, entries, submissions, evaluations, incidents, audit_log, auth_limits, ai_panels, ai_runs, question_bank, question_assignments.

001 creates the initial round/team schema; legacy submission columns are adapted by 003. 002 adds panel jobs/rosters and score provenance. 003 renames uploaded_by to submitted_by, adds source_type and permits null legacy file fields without deleting records. 004 adds empty question-bank/assignment tables and submission-assignment FK. scripts.create_tables applies numbered SQL files in order. No migration is auto-run at startup, and table setup does not import questions.

Legacy API/database names upload_seconds, upload_ends_at and action close_uploads are retained for migration compatibility, but now mean submission time/deadline/closure. UI labels refer to direct submissions. Do not reintroduce file upload controls because of those old names.

Apply all migrations and import banks before starting a new competition. Do not retrofit random assignment silently into an already-running legacy round. Existing historical records are retained, but new grading expects the submission's assigned-question linkage.

## Direct submission contract

POST /api/rounds/{id}/submissions takes attempts[{prompt,answer}] and selected_attempt only. Team identity and assigned question are derived on the server. Prompt limit 16000 chars, answer 24000, aggregate content defaults to 262144 UTF-8 bytes. Attempts must be nonempty and within stage limit. Text is not stripped. Client-supplied team/question IDs are not accepted.

Save draft → review → confirm. No draft auto-submission. Latest confirmed version wins; previous versions are retained. Maximum 10 saved versions per team/stage. Confirmation is idempotent under concurrent team-member requests. Older drafts cannot replace newer confirmed versions. A direct content hash covers exact strings plus selected index, recomputed on confirmation if selection changes. Confirmed versions are immutable.

Unsaved editor text is held in browser memory only, updated on each input/add/remove. Saved versions reload from PostgreSQL. Editing dismisses a stale confirmation preview. Sign-out/expired session clears private in-memory state. Polling does not wipe active input; server deadlines and editor lock still apply. Practice validates without storage, scoring or assignment.

## Model panel and approval

Rubrics: Fix target_accuracy50/prompt_efficiency30/creativity_clarity20; Word Ban task_accuracy30/banned_word_compliance30/prompt_effectiveness20/creativity20; Recreate target_accuracy50/prompt_efficiency30/creativity20.

Queue panels per candidate or whole stage after submission closure. The separate evaluation worker defaults to 2 concurrent submissions × 4 parallel model requests. Startup/import/login/assignment/submission do not invoke providers. Each candidate's selected prompt/answer is the scored attempt, with other attempts available as context and human evidence. The correct assigned target/rules are frozen into the job.

Exactly four successes are required for a combined suggestion. Average each criterion equally across the four, round half up to two decimals, sum those means. No missing-model zero or silent reweighting. Spread >=15 marks flags disagreement. Deterministic compliance corrections are disclosed with reported/used values.

Judges explicitly approve official scores and write comments; AI never approves or publishes. Approval records source run ID or explicit manual_override. Pending jobs block approval/publication. Outages can be handled by failed-model retry or cancellation followed by audited manual override. Successful model results are retained on retry; complete panels are not resampled; max 4 runs/submission. Worker interruptions preserve partial results and expire leases to incomplete; explicit retry is required. Superseded/cancelled work cannot overwrite current results. In-flight requests may still incur provider charges.

## Setup and transfer

The private environment has not been printed. Missing provider keys/defaults were appended without changing existing values. Configure GROQ_API_KEY, exactly three distinct accessible GROQ_EVAL_MODELS, OPENAI_API_KEY and optional OPENAI_EVAL_MODEL (default gpt-4.1-mini). Set exact FRONTEND_ORIGINS and secure cookies for production. Restart server and worker after environment changes; an existing stage retains its frozen model IDs. Old GROQ_MODEL, STORAGE_BUCKET and MAX_UPLOAD_BYTES are unused. MAX_SUBMISSION_BYTES is the current size setting.

Move the entire folder including backend/data, docs and local assets. .env is ignored by Git and must be transferred privately. Question answers are confidential server data; do not expose backend/data as static assets or a public repository. Original competition DOCX is retained in docs as source; newer user instructions take precedence.

## Remaining operator work

1. Get permission before executing code if not already granted by a later user message.
2. Install, validate imports/syntax/runtime, apply migrations 001–004 and bootstrap the organiser explicitly.
3. Review the manually extracted data against original source files; run the import dry-run, then the actual import when authorised. No questions are in Supabase from our work yet.
4. Configure Supabase email OTP delivery/template (shared project changes may affect the old website), provider keys and available model IDs.
5. Start the web server and evaluation worker explicitly; test the full 22 → 11 → 5 workflow and per-team question grading.
6. Complete docs/MANUAL_ACCEPTANCE.md, especially assignment privacy, balance, no rerolls, text preservation, concurrent confirmation, deadlines, provider failure, ties and approval.
7. Configure production HTTPS/proxy/origins, mail/database capacity, backups and external-LLM volunteer procedures.

No audience voting, payments, public signup, phone/browser monitoring, automated surprise tie-break runner, result retraction UI or existing-role editing UI is included. External LLM authenticity, actual attempt counts and unedited-output compliance require volunteer verification.

## Configured Groq model IDs

At the user's request, GROQ_EVAL_MODELS in backend/.env and backend/.env.example is set to:
openai/gpt-oss-120b,openai/gpt-oss-20b,qwen/qwen3.8-27b

These IDs were checked against official Groq documentation. The first two are production models; Qwen 3.8 27B is listed as preview. Account-specific permissions and inference are unverified; no Groq API call or application code was run. These are Groq-hosted models even though the GPT-OSS IDs begin with openai/. The separate OpenAI API evaluator remains gpt-4.1-mini. Existing secrets were preserved. Model IDs are already populated; setup still needs valid provider keys. Restart both processes after environment changes; existing round rosters remain frozen.

### Local setup clarification — 2026-10-30

The user confirmed the existing Supabase project is the intended target and changed the immediate deployment to local testing. Configured FRONTEND_ORIGINS for http://127.0.0.1:8000 and http://localhost:8000, and COOKIE_SECURE=false for local HTTP. This supersedes the production HTTPS configuration above. The organiser email is still required before bootstrap/import. The user has not yet explicitly requested starting a process or running tests; the earlier restrictions remain in effect. Production later requires exact HTTPS origins and COOKIE_SECURE=true.