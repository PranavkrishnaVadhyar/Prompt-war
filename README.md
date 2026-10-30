# Prompt War

## Password sign-in (current behaviour)

PromptWar now uses approved email + password sign-in only. The email-code UI and /api/auth/otp/start and /api/auth/otp/verify routes were removed. Existing Supabase passwords, session cookies, CSRF protection, throttling and role approval remain in place. SMTP is not required for password sign-in. Older OTP instructions below are historical.

No passwords were changed automatically. Existing users can use their Supabase password. For an approved user needing a password, run from backend in an interactive terminal:

```powershell
.\.venv\Scripts\python.exe -m scripts.set_password --email bpranavkrishnaofficial@gmail.com
```

The command confirms the email and prompts twice with hidden input; passwords are never command-line arguments or saved to files. It changes the shared Supabase identity password, so the change also applies to VYUHAM if the identity is used there. It requests no recovery email. Use the same command with the appropriate approved member email after enrolling new participants/staff. New identities otherwise have unknown random passwords. No public self-registration/reset endpoint was added.

Restart the backend and hard-refresh the browser after these source changes. Source inspection only: no tests, server starts or password updates were executed by the agent for this change. Runtime sign-in remains to be checked by the user.

Standalone VYUHAM ’26 competition project for Digital University Kerala, supported by Reflections. The frontend is HTML/CSS/JavaScript with VYUHAM branding; the backend is FastAPI and Supabase Auth/PostgreSQL. Participants paste prompts and plain-text AI answers into fields. Three Groq models and one basic OpenAI model independently assess the selected attempt, with human approval required for every official score.

**Execution status:** source files and extracted question data were written only. No application code, installation, syntax check, test, server, database migration, question import or model API call has been executed. Runtime validation remains pending.

## Event sequence

| Stage | Challenge | Source bank | Default teams | Work time | Submission time | Progression |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Fix the Output | Original Round 2 | 22 | 10 minutes, max 5 attempts | 5 minutes | Top 11 |
| 2 | Live Word Ban Showdown | Original Round 3 | 11 | 2 minutes, 1 prompt | 5 minutes | Top 5 |
| 3 | Recreate the Target | Original Round 1 | 5 | 10 minutes, max 5 attempts | 5 minutes | Winner and runner-up |

The original Round 1 is held last. Each stage completes briefing → timed challenge → direct submission → evaluation/break → published results before the next stage begins. Scores reset at each stage.

The admin's **Start & assign random questions** action assigns one question per eligible team and starts the common clock atomically. Questions come from the bank matching the challenge kind, not the stage number. Shuffled cycles avoid repeats while unused questions remain. With 22 teams and 11 questions, each question is used twice; 11 teams receive distinct questions and five finalists receive a distinct random subset. Assignment snapshots survive refreshes, pauses, extensions and service restarts. Each team is evaluated against its own assigned target.

## Layout

```text
PromptWar/
  PROJECT_CONTEXT.md               Read first in the next chat
  AGENTS.md
  README.md
  frontend/
    index.html
    assets/                        Local VYUHAM / DUK branding
    css/app.css
    js/config.js                   Public API origin only
    js/app.js
    js/entry.js                    Plain-text attempt editor
    js/panel.js                    Four-model scorecards
  backend/
    .env                           Private copied credentials, ignored by Git
    .env.example
    requirements.txt
    app/                           Auth, rounds, questions, submissions, evaluation
    data/question_bank.json        33 extracted questions; not a browser asset
    data/sources/                  Original three supplied Markdown banks
    sql/001_prompt_war.sql
    sql/002_evaluation_panels.sql
    sql/003_direct_submissions.sql
    sql/004_question_banks.sql
    scripts/create_tables.py
    scripts/bootstrap_organiser.py
    scripts/import_questions.py
    scripts/evaluation_worker.py
  docs/                            Setup, API, formats, banks, evaluation and checks
```

All paths resolve relative to this project. Move the whole folder together; it does not import the original VYUHAM backend or depend on Downloads/OneDrive paths.

## Setup later

These are operator instructions, not executed commands. Read docs/SETUP.md first. From backend, using Python 3.11 or later:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m scripts.create_tables
python -m scripts.bootstrap_organiser --email YOUR_ORGANISER_EMAIL
python -m scripts.import_questions --dry-run
python -m scripts.import_questions --organiser-email YOUR_ORGANISER_EMAIL
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. FastAPI serves frontend/ at / and the backend at /api. There is no npm build. The table setup command applies all numbered SQL files; it **does not import questions**. The import is a separate explicit operation. Migration 004 creates empty question tables only.

For AI assessment, configure the provider settings and run a second process from backend with the same environment:

```powershell
python -m scripts.evaluation_worker
```

Nothing invokes providers unless an organiser/judge queues work and the worker processes it. Setup, startup, login, question assignment and saving answers do not call evaluation models.

## Submissions and storage

Teams paste each exact prompt and unedited answer into separate text fields, select an attempt, save a draft, review it and confirm. No JSON authoring or file upload is required from participants; the browser serializes the fields automatically. Data is stored directly in prompt_war.submissions as JSONB plus identity, assignment, version and receipt metadata.

The latest confirmed version is judged. Drafts never count automatically. Confirmed versions are immutable; corrections require a new version and confirmation before the deadline. Maximum ten saved versions per team/stage, with attempt limits 5/1/5. The content hash covers the exact prompt/answer strings and confirmed selected attempt in canonical UTF-8 JSON. Server validation preserves text whitespace.

Supabase Storage is not required for new submissions. Migration 003 retains legacy parsed records and nullable old file metadata without deleting any bucket or old object. The app no longer uploads/downloads submission files. CSV result exports remain available to organisers.

## Evaluation and access

- Approved personal-email OTP or existing-account password login; no public signup.
- Participant, volunteer, judge and organiser permissions checked on the server.
- Organiser-only question-bank previews, saved assignment roster and candidate/member details.
- Participants receive only their own assigned question when the round starts; private question guidance is not exposed to them.
- Judges see anonymous submission labels, assigned question/reference, all submitted attempts and four individual model scorecards.
- Exactly three distinct configured Groq model IDs plus one OpenAI evaluator, default gpt-4.1-mini. Equal-weight criterion means produce the suggested total only after all four succeed.
- Human approval links to the completed panel, or an explicit audited manual override after failed/pending work is resolved.
- Banned-word compliance is authoritative 0/30. Word Ban source banks include published singular/plural variants; the expanded match list is frozen with the assigned question.
- Ties affecting qualification/prize places block publication until a surprise tie-break is recorded.

## Environment and transfer

backend/.env was copied privately from the original VYUHAM backend. It initially points at the same Supabase project, with shared Auth users but separate prompt_war tables. Missing evaluation keys/defaults were appended without exposing or overwriting existing secrets.

Configure DATABASE_URL, SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY. Configure GROQ_API_KEY, GROQ_EVAL_MODELS (three distinct available IDs), OPENAI_API_KEY and optional OPENAI_EVAL_MODEL for panel assessment. MAX_SUBMISSION_BYTES defaults to 262144. FRONTEND_ORIGINS must match the browser origin; COOKIE_SECURE must be true for production HTTPS.

.env is ignored by Git, so transfer it separately and privately when moving through Git. Keep the question bank and reference answers confidential; backend/data is outside the web root and is not served as static content. Do not publish the entire project directory as a static website.

## Limits and validation

External LLM use means direct text cannot prove generation time, total attempts or whether the answer was edited. Volunteers and saved chat history remain necessary. The app does not monitor external browser tabs, collect phones, process payments or provide public signup. New question import and migration changes should be applied before the competition, not halfway through a live round.

Use docs/MANUAL_ACCEPTANCE.md after permission to execute the project. See docs/QUESTION_BANKS.md, docs/SUBMISSION_FORMAT.md and docs/EVALUATION_PANEL.md for the detailed contracts.

## Configured Groq model IDs

At the user's request, GROQ_EVAL_MODELS in backend/.env and backend/.env.example is set to:
openai/gpt-oss-120b,openai/gpt-oss-20b,qwen/qwen3.8-27b

These IDs were checked against official Groq documentation. The first two are production models; Qwen 3.8 27B is listed as preview. Account-specific permissions and inference are unverified; no Groq API call or application code was run. These are Groq-hosted models even though the GPT-OSS IDs begin with openai/. The separate OpenAI API evaluator remains gpt-4.1-mini. Existing secrets were preserved. Model IDs are already populated; setup still needs valid provider keys. Restart both processes after environment changes; existing round rosters remain frozen.
