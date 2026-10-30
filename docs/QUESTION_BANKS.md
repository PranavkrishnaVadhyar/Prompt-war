# Question banks and random assignment

The supplied three Markdown banks have been manually extracted to backend/data/question_bank.json. It contains 33 questions: 11 Recreate, 11 Fix and 11 Word Ban. Original files are preserved in backend/data/sources. No extraction/import program, SQL or application has been run and no questions have been inserted into Supabase.

## Round mapping

| Source file | Source label | Challenge kind | Actual competition stage |
| --- | --- | --- | --- |
| round_2_question_bank.md | Round 2 | fix | Stage 1, 22 teams |
| round_3_question_bank.md | Round 3 / final | word_ban | Stage 2, 11 teams |
| round_1_question_bank.md | Round 1 | recreate | Stage 3, 5 finalists |

This follows the user's instruction that the original Round 1 is held last. The old source wording about a shared Word Ban task/final stage is superseded by the user's later request for per-team random questions and the agreed stage order.

## What was extracted

- Stable key, original round, source question number, title and challenge kind.
- The description as the participant task for Fix/Recreate, and the AI Task for Word Ban.
- Exact target text, indentation, internal blank lines, Unicode and Markdown formatting, without the surrounding source code fences.
- Original flawed input for Fix challenges, including internal code fences in The Verbose Coder.
- Word Ban lists. The Prompt Engineering Challenge guidance is retained as private judge_notes, not a participant hint.
- Common participant rules derived from the source operational sections.

The JSON is a structured data artifact, not a script. Source inconsistencies were not silently corrected: e.g. table dimension descriptions and phrasing/capitalization constraints are preserved alongside the supplied target. Organisers should review the private preview and original files before the first briefing. The target content is not executed as YAML, XML or Python.

## Create tables later

Migration 004_question_banks.sql creates prompt_war.question_bank and prompt_war.question_assignments, and links new submissions to their assignment. It creates no question rows. The setup script applies migrations 001–004 in filename order when explicitly run.

## Import later

From backend, after approving an organiser, the operator may run:

```powershell
python -m scripts.import_questions --dry-run
python -m scripts.import_questions --organiser-email YOUR_ORGANISER_EMAIL
```

Neither command has been run during authoring. Dry-run validates and prints counts without a database connection. The actual import requires an approved organiser email for the audit actor. Optional --file selects another structured JSON bank.

The import validates fields and challenge/source-number coherence, computes content hashes and inserts/updates by stable key. Unchanged repeated imports do not duplicate questions or reactivate intentionally disabled rows. No missing question is deleted automatically. Changed/new questions cannot be imported after the corresponding briefing opens or assignments exist; the import transaction rolls back. Identical imports remain harmless after start.

## Admin initiation and randomness

Importing, logging in or opening a page assigns nothing. The organiser releases briefing, then clicks Start & assign random questions for that stage. In a single transaction, the backend:

1. Locks the round and eligible entries.
2. Reads the active bank matching round.kind.
3. Uses a system cryptographic random generator to shuffle teams and question cycles.
4. Uses each bank question once per shuffled cycle, reshuffling for each additional cycle if there are more teams than questions.
5. Saves one question snapshot per team and starts the common deadlines.

If any assignment/start step fails, both are rolled back. Repeated Start does not reroll assignments. With 22 teams and 11 questions, every question is used twice. With 11 teams each gets a different question; five finalists get a distinct random subset of 11. Counts remain balanced even if attendance differs. This balances repetition frequency, not intrinsic difficulty; organisers should review challenge difficulty before importing.

## Privacy, persistence and grading

Before Start, participants see no bank or assigned target. After Start, the server returns only that team's saved question, target/flawed input and bans. Original bank files are outside frontend and cannot be retrieved from the static web root. Private judge notes are available only to organiser/judge views.

Question snapshots are frozen. Refreshes, pause/resume, extensions and later bank edits do not change a team's assigned material. The organiser's Questions & assignments screen shows the bank and saved team/computer mappings. Judges see the assigned question alongside each anonymous submission.

A submission derives its assignment from the authenticated team; clients cannot choose another question. A composite database foreign key enforces matching assignment/team/round. All four LLMs and human score validation use that assigned question's target and checks. Evaluation jobs retain the assignment ID, question key and hash. CSV exports include assignment/question provenance.

## Word Ban plural forms

The source says capitalization and pluralization must not bypass bans. The importer generates explicit English singular/plural variant sets, including supplied irregulars such as leaf/leaves and money/monies, and stores them in each question snapshot. Participants can expand the published forms in the challenge view. These exact listed forms are matched case-insensitively as whole words/phrases. Arbitrary stemming or substring blocking is not claimed. Inspect the preview if additional language-specific forms are required before the bank locks.

A match zeros only the compliance criterion. Literal missing flawed-context and copied-target/similarity flags assist review; they do not automatically disqualify a team.
