# Four-model evaluation and judge approval

Each round's latest confirmed team submission is assessed by exactly three Groq-hosted models and one basic OpenAI model. All four independently receive the same task, rubric, automatic checks and submitted attempts, with the selected attempt identified as the item to score. No evaluator sees another evaluator's assessment. Account/team metadata is not added to the provider evidence, though participants' own submitted text may contain personal information.

## Configuration

Add the following to backend/.env. Empty/default entries have been appended where missing; no existing secret was overwritten.

```dotenv
GROQ_API_KEY=YOUR_GROQ_KEY
GROQ_EVAL_MODELS=openai/gpt-oss-120b,openai/gpt-oss-20b,qwen/qwen3.8-27b
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_EVAL_MODEL=gpt-4.1-mini
EVALUATION_WORKERS=2
EVALUATION_TIMEOUT=60
```

Use three distinct Groq model IDs actually accessible to your account and supporting JSON Object Mode. Availability and entitlement differ by account. Select IDs from the [official Groq model catalog](https://console.groq.com/docs/models); do not assume an older Llama or Qwen ID remains available. The configured roster was selected from the official Groq documentation: GPT-OSS 120B, GPT-OSS 20B and Qwen 3.8 27B. Qwen is currently a preview model. Access and inference have not been tested with your account; confirm its availability before event use. No model is silently substituted if it fails. The former GROQ_MODEL field does not configure this panel.

The default OpenAI evaluator is [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini). It uses the Responses API with strict [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses), store=false and no tools. Groq uses its Chat Completions API and [JSON Object Mode](https://console.groq.com/docs/structured-outputs); the backend independently validates every score and explanation. Provider access and billing have not been checked during authoring.

Use version-pinned model identifiers where your providers offer them. The request model IDs are frozen in ai_panels when a round's first panel is queued, and each successful response's returned model identifier is recorded. Changing the environment does not change the existing round's roster. API keys remain only in the server environment.

## Database and worker

Apply 002_evaluation_panels.sql after the initial migration. scripts.create_tables applies both migrations in order when explicitly run. No migration has been executed during authoring.

Run `python -m scripts.evaluation_worker` separately from the FastAPI process, from the backend directory with the same environment. By default, two candidate submissions are processed concurrently, each using four parallel model requests: up to eight provider requests at once. Lower EVALUATION_WORKERS if provider quotas require it. One worker process is recommended unless total concurrency has been deliberately reviewed; multiple processes each apply their own worker limit.

Nothing queues a job merely by logging in, uploading a file or opening a screen. After submission closure, an organiser or judge clicks Evaluate all final submissions, or requests one candidate's panel. The batch skips already-approved submissions and candidates with an active submission extension. Jobs are durable database records rather than long-running web requests.

## What is stored and displayed

For every candidate, the Judging screen shows:

- The selected prompt and AI answer, other submitted attempts, confirmation timestamp and saved submission details.
- Automatic banned-word, target-match, similarity and copying flags.
- Four model cards with provider, requested model, returned model, criterion scores, total, criterion explanations, overall explanation and response timing.
- Error status for failed/refused/invalid/incomplete responses, rather than an invented score.
- The combined suggested score, criterion means and range between highest and lowest model totals.
- Prior evaluation runs, successful retained results and retry status.
- Human-approved criteria, total, comments and optional surprise tie-break score.

Organisers see team names, member emails and workstation alongside the submission. Judges use anonymous submission labels and do not receive the team roster. Identifying text volunteered inside a prompt/file cannot be automatically anonymised reliably.

## Combined score

Every evaluator uses the existing round rubric, with a maximum total of 100. All four models have equal weight, 25 percent each. For every criterion, add the four validated scores and divide by four, rounding half up to two decimal places. Sum those rounded criterion means to obtain the combined suggested final score. It may differ by a cent from averaging the four displayed totals because rounding is applied per criterion.

No combined score is created until all four evaluators succeed. A missing model is never treated as zero and never causes the remaining models to be reweighted silently. If the highest and lowest model totals differ by 15 or more marks, the screen flags the disagreement for review; this does not change the marks automatically.

Banned-word compliance remains deterministic. The backend sets this criterion to 0 when a configured banned word/phrase matches, otherwise 30. If a model proposes a different compliance mark, its reported value is preserved and the adjustment is disclosed. Other score criteria still require valid numeric values within their rubric maxima and at most two decimal places.

## Approval and publication

Use Fill combined scores to populate the human scoring form. This does not approve anything. Review every assessment and the underlying submission, adjust marks where justified, add the judge's reasoning and click Approve official score. The approved score records the source evaluation-run ID. Subsequent qualification and winners use the approved human total, never an unapproved AI total.

An active queued/running panel blocks approval and publication. If providers fail, either retry the failed/missing evaluators or explicitly cancel a pending job with a reason. Once no job is active, judges can select the manual-override checkbox and record why they are approving without a complete panel. The override and its comments are saved in the score and audit log. A manually approved submission cannot later start a new panel unnoticed. This fallback preserves the original manual judging capability without treating partial AI scores as complete.

## Failures and retry policy

Each provider has a bounded timeout. Authentication errors, model access errors, rate limits, invalid JSON, refusals and bad score ranges become explicit error cards with no marks. The UI can retry only failed/missing evaluators; successful evaluations are copied unchanged into the retry's history. Completed panels are returned as-is if requested again, rather than resampling for more favourable scores. At most four panel runs are permitted per submission.

Queued jobs survive restarts. A running job has a five-minute lease, renewed as results arrive. If the worker dies, its stale lease becomes incomplete after the worker resumes; a judge explicitly retries the unfinished evaluators. The system does not silently repeat possibly billed calls. Cancellation cannot reliably stop provider requests already in flight, but cancelled runs cannot accept their eventual results.

An submission extension or disqualification supersedes the candidate's old evaluation runs. The worker checks round state and submission eligibility again before saving results; stale jobs cannot approve or overwrite a replacement. Round publication is also blocked while any panel remains queued or running.

## Execution status

No Python/JavaScript application code, worker, provider request, migration or test has been executed during authoring. Configure credentials and model access, explicitly apply the new migration, then validate the complete workflow before using real competition submissions.


## Assigned question and direct entry update

Submissions are pasted plain-text prompts and answers stored in PostgreSQL; no file is uploaded or required. Every team receives a stable random question snapshot when the admin starts its round. Model evidence and human checks use that team's assigned task, expected target/flawed input, bans and participant rules. The job stores assignment/question IDs and a question-content hash for audit. Judges see the correct question above each submission; no global shared target is used. Apply migrations 003 and 004 and import the extracted bank explicitly before a new event. These operations have not been executed during authoring.
