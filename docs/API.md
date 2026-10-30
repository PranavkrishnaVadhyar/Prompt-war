# API map

Base path /api. Approved session cookies are required except for health and authentication entry points. Mutations require an allowed Origin and X-CSRF-Token from GET /auth/session. No provider key or Supabase credential is returned to the browser.

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | /health | Public | Process liveness, not DB readiness |
| GET | /auth/session | Public | CSRF cookie/token |
| POST | /auth/login | Public, throttled | Existing-account password login |
| POST | /auth/refresh | Refresh cookie | Rotate session cookies |
| POST | /auth/logout | Browser session | Revoke local session and clear cookies |
| GET | /auth/me | Approved member | Role/team membership |
| GET | /dashboard | Approved member | Stage state, own outcomes and server time |
| GET | /rounds/{id}/workspace | Enrolled team or staff | Own assigned question after Start, own saved answers; staff configuration |
| POST | /rounds/{id}/submissions | Eligible team in submission window | Save direct attempts/selected index as a draft, linked to server-selected assignment |
| POST | /submissions/{id}/confirm | Owning team in window | Confirm selected attempt, content hash and receipt |
| GET | /submissions/{id} | Owning team; judge/organiser after closure | Stored text/receipt metadata, never a file URL |
| POST | /practice/preview | Participant | Validate direct text without saving/scoring |
| GET | /rounds/{id}/results | Approved member | Published results only |
| POST | /incidents | Approved member | Own-team incident; staff can select a team |
| GET | /admin/overview | Volunteer, organiser | Teams, assignments to computers, submission state and incidents |
| GET | /admin/questions?kind=fix | Organiser | Private full question bank; kind optional |
| GET | /admin/rounds/{id}/assignments | Organiser | Saved random question snapshots and team/computer mappings |
| POST | /admin/teams | Organiser | Enrol team and approve users |
| PUT | /admin/teams/{id}/allocation | Organiser | Reassign computer with reason |
| POST | /admin/staff | Organiser | Approve staff |
| PUT | /admin/rounds/{id} | Organiser before briefing | Title, optional shared instructions, timing, qualifiers and LLM instructions |
| POST | /admin/rounds/{id}/action | Organiser | brief, start, pause, resume, end_challenge, close_uploads, close |
| POST | /admin/rounds/{id}/extensions | Organiser | Audited individual direct-submission extension |
| POST | /admin/rounds/{id}/disqualify | Organiser before publication | Record reason and exclude team |
| POST | /admin/rounds/{id}/publish | Organiser | Rank approved results and advance teams |
| GET | /judge/rounds/{id}/queue | Judge, organiser after closure | Final text submissions, each assigned question, checks, panel history and approvals |
| GET | /judge/rounds/{id}/panel | Judge, organiser | Frozen/requested model IDs and readiness, no keys |
| POST | /judge/rounds/{id}/evaluate | Judge, organiser | Queue unapproved final submissions |
| POST | /judge/submissions/{id}/suggest | Judge, organiser | Queue/retrieve a four-model panel |
| POST | /judge/submissions/{id}/retry-panel | Judge, organiser | Retry failed/missing evaluators only |
| POST | /judge/submissions/{id}/cancel-panel | Judge, organiser | Cancel pending work with a reason |
| PUT | /judge/submissions/{id}/score | Judge, organiser | Approve human criteria/tie score with completed panel or explicit override |
| GET | /admin/audit | Organiser | Latest 200 audit events |
| GET | /admin/export | Organiser | CSV with submission, approved score and assigned-question provenance |

Start creates random assignments and common deadlines atomically. There is no participant endpoint for selecting/rerolling a question and no HTTP question-import/write endpoint; import is an explicit operator CLI script.

Direct submission accepts only attempts[{prompt,answer}] and selected_attempt. Text answers need not contain JSON. The browser serializes the request automatically; identity/question IDs are server-derived. See SUBMISSION_FORMAT.md.

Legacy internal field names upload_seconds/upload_ends_at and action close_uploads now refer to submission time/deadline/closure. Old template/file endpoints and multipart uploads are removed. All actual submissions are direct text; CSV exports remain downloadable.

The organiser sees candidate/member details; judges see anonymous labels with the correct assigned task and target. Every model and human score uses that assigned snapshot. Provider requests run only in the separate worker after an explicit evaluation request.
