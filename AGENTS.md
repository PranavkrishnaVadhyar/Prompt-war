# Prompt War handoff

Read PROJECT_CONTEXT.md and README.md before changing this project.

The user required a separate frontend/ and backend/, FastAPI, Supabase and plain HTML/CSS/JS. Preserve this architecture and keep paths portable when the project moves.

The user explicitly prohibited executing code during initial creation. No application code, dependency installation, syntax check, test, server, setup script or database SQL has been run. Do not execute them unless subsequent user instructions authorise it. Source reads and file edits are allowed.

Never print or commit backend/.env. It was copied privately from the existing VYUHAM backend and may initially point to a shared Supabase project. Only the frontend directory may be served as static content.

The original Round 1 is held last. Each stage separately completes work, submission, evaluation, result publication and qualification. Preserve the 22 → 11 → 5 progression by default and human approval of all official scores.

Submissions are direct plain-text fields, not file uploads. Three original-numbered question banks are extracted in backend/data/question_bank.json; do not insert them without later user authorisation. scripts.import_questions performs the explicit import. Admin Start randomly assigns stable per-team question snapshots, matched by challenge kind, and grading must use the team's own assigned question. Preserve the fixed assignment across refreshes/extensions; do not reroll it.

