# Manual acceptance checklist

None of these checks has been run. Complete them in a staging Supabase project after permission to execute the app. Use the real event computers and designated external LLM before event day.

## Setup and permissions

- [ ] Dependencies install; Python/JavaScript imports and the app/worker run without errors.
- [ ] Migrations 001–004 create only the intended prompt_war schema objects; repeat application preserves data.
- [ ] Table setup does not import questions, start rounds, send email or call models.
- [ ] Moving the entire folder preserves frontend, environment, data and script paths.
- [ ] No environment/target-bank files are retrievable from the web root or committed publicly.
- [ ] Bootstrap the organiser; approve judges, volunteers and individual/two-member teams.
- [ ] OTP delivery/template, password login, expiry refresh and logout work; no tokens/text in localStorage.
- [ ] Unapproved accounts, wrong roles, wrong teams and nonqualified teams cannot access protected resources.
- [ ] Wrong Origin/CSRF and invalid/oversized bodies are rejected without exposing secrets.
- [ ] Team cap 22, member cap 2, unique email rules and enrolment freeze at first briefing work.
- [ ] Existing Supabase users retain passwords and unrelated roles. Workstation reassignments are audited.
- [ ] Real proxy/NAT/email limits support shared-network sign-in.

## Extraction and import

- [ ] Compare all 33 extracted questions with the original files, including indentation, blank lines, Unicode and inner Markdown fences.
- [ ] Validate 11 questions per kind; mapping is Fix/source Round2 first, WordBan/source Round3 second, Recreate/source Round1 last.
- [ ] Dry-run validates counts without any DB connection. Actual import requires an approved organiser and writes only on explicit invocation.
- [ ] Repeated identical imports do not duplicate questions or re-enable deliberately disabled rows.
- [ ] A malformed/new/changed bank during briefing or after assignments exists rolls back without partial writes.
- [ ] Private Word Ban guidance is retained but never shown to participants.
- [ ] Review source wording/target inconsistencies and expanded English plural forms before briefing.

## Random assignment

- [ ] Login, refreshing, importing and briefing assign nothing or reveal a participant target.
- [ ] Admin Start assigns exactly one matching-kind question per eligible team and starts common deadlines in one transaction.
- [ ] 22 teams/11 questions use every question twice; 11 teams get distinct questions; five finalists get a distinct random subset.
- [ ] Arbitrary attendance produces balanced usage counts differing by at most one when the bank is sufficient.
- [ ] A failed start, missing bank or failed insert rolls back both assignments and timer changes.
- [ ] Double/concurrent Start does not create duplicates or reroll assignments.
- [ ] Refresh, re-login, restart, pause/resume and submission extension retain the same assigned snapshot.
- [ ] Participants cannot fetch other questions, bank data, another team's assignment, or private judge notes.
- [ ] Organiser sees saved team/computer/question mappings; judges see only the candidate's assigned question in evaluation.
- [ ] Client-supplied team/question/assignment IDs are rejected in direct submission payloads.
- [ ] Composite DB FK prevents cross-team/round assignment linkage.

## Direct entry and lifecycle

- [ ] Task/target/bans appear only at Start, with fixed server deadlines. Another active stage cannot overlap.
- [ ] No file chooser, template or JSON-authoring requirement is present in the participant flow.
- [ ] Paste multiline Unicode, Markdown/XML/code text; exact whitespace reaches the DB and grading unchanged.
- [ ] Add/remove attempts safely; selected index remains valid. Word Ban permits only one attempt.
- [ ] Reject blank/whitespace-only/null/invalid-Unicode text, excess lengths, oversized totals and invalid selections.
- [ ] Typed editor state survives polling and add/remove; sign-out/expired session clears private memory.
- [ ] Unsaved reload warns; saved drafts restore from DB. Practice validates without saving or scoring.
- [ ] Save creates a draft preview only; editing dismisses stale confirmation preview.
- [ ] Confirmation creates an immutable timestamped receipt and correct content hash for the final selection.
- [ ] Draft-only submissions never become final automatically at deadline.
- [ ] Later confirmed versions replace earlier ones; unconfirmed versions do not. Old drafts cannot override newer confirmed versions.
- [ ] Repeated/concurrent confirmations from both team members preserve the original receipt and respect deadlines/version limits.
- [ ] Round closure vs confirmation races follow round → entry lock ordering.
- [ ] Pause disables submission while preserving typed state; resume shifts deadlines consistently.
- [ ] A new submission extension retains the original question, invalidates provisional assessments and affects only that team.

## Evaluation and results

- [ ] Every candidate is checked against its own assigned target, never the old shared round target or another candidate's question.
- [ ] Banned-word matches use published case-insensitive whole-word/phrase variants. No unrelated substring false positives.
- [ ] Compliance is 0 with a banned match and 30 otherwise; only this criterion is automatically zeroed.
- [ ] Missing literal flawed input, similarity and target-copy signals are advisory and visible for review.
- [ ] Three distinct Groq models and one OpenAI model run independently for each selected attempt using the same candidate question/rules/rubric.
- [ ] Worker concurrency is bounded; partial results are saved/displayed; a missing/refused/invalid model produces no aggregate.
- [ ] Verify equal criterion means, rounding, total and >=15-point disagreement flag with known values.
- [ ] Model-reported compliance corrections are disclosed; provider reasoning is rendered as text, never executed.
- [ ] Retry only failed/missing evaluators, preserve successes, cap runs and prevent completed-panel resampling.
- [ ] Worker restart/lease expiry retains progress; explicit retry is required rather than silently repeating billed work.
- [ ] Cancellation, extension or disqualification prevents late/stale results from affecting the current candidate.
- [ ] Candidate prompt, answer, all attempts, assigned question and all model scorecards are visible before judge approval.
- [ ] Pending jobs block approval/publication. Complete panel or explicit audited manual override is required.
- [ ] Official scores retain source run/override, judge comments and surprise tie-break evidence.
- [ ] Missing submissions/disqualified teams do not qualify; pending extensions/unapproved final submissions prevent publication.
- [ ] Qualification/prize-boundary ties block publication until an externally conducted tie-break is recorded.
- [ ] Scores reset between stages; top 11 then 5 advance; Recreate is last and produces winner/runner-up.
- [ ] CSV includes exact attempts, scores, model provenance and assigned-question key/title; formula injection is neutralised.

## Event readiness

- [ ] Volunteers verify external LLM attempt counts, original input usage, unedited answers and phone collection in person.
- [ ] Test database/Auth/provider capacity with realistic concurrency and actual accounts.
- [ ] HTTPS, secure cookies, exact origins, proxy trust, private backups and fallback/manual procedures are ready.
- [ ] Do not migrate a live legacy competition halfway through a round; use the new assignment flow before event start.
