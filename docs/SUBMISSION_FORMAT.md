# Direct prompt and answer submissions

Participants enter ordinary text into the interface. They do not write JSON or upload a file.

## Participant flow

1. Work in the designated external LLM during the timed challenge.
2. When the submission window opens, paste the exact prompt and unedited AI answer into the matching fields.
3. Add all actual attempts, within the round limit: five for Fix/Recreate and one for Word Ban.
4. Select the attempt to be judged and click Save draft & review.
5. Inspect the saved preview, then explicitly confirm the final submission before the deadline.
6. Check the server timestamp and receipt. A saved draft alone does not count as a final submission.

Saving creates a new immutable draft version. To correct text, edit the entry form and save a new version, then confirm that version. The latest confirmed version is judged; a later unconfirmed draft does not replace it. Up to ten saved versions are allowed per team/stage. This version limit does not permit extra LLM attempts.

Each prompt accepts up to 16000 characters and each answer 24000. Combined canonical UTF-8 submission content defaults to a 262144-byte limit. Empty/whitespace-only content, null characters, invalid Unicode, too many attempts and invalid selected attempt numbers are rejected. Text whitespace is preserved for exact-format targets. Supabase JSONB stores the strings; it does not mean participant answers must be JSON.

## Draft persistence

Typed unsaved text is held in browser memory so polling and adding attempts do not discard it. It is not kept in localStorage on shared computers. Save a draft to persist it to the database. Reloading or closing the browser before saving can lose typed text; the app warns about unsaved changes. Sign-out clears the editor state. Saved versions can be reopened through Submission history.

When an editor is changed, its old confirmation preview is dismissed so the team does not accidentally confirm a different saved text. Confirmation locks the stored version and records the chosen attempt and server time. Repeated confirmation returns the original receipt. A newer confirmed version cannot be overwritten by an older draft.

## Practice

Practice entry uses the same fields and validation, without storing answers or affecting results. It permits up to five attempts for learning the interface; the real Word Ban round permits only one. Practice does not assign a question or invoke any model.

## Backend API contract for developers

The frontend automatically sends this structure to POST /api/rounds/{round_id}/submissions:

```json
{
  "attempts": [
    {"prompt": "Exact prompt as plain text", "answer": "Exact unedited AI answer"}
  ],
  "selected_attempt": 1
}
```

The server derives team identity from authentication, round identity from the path and assigned question from question_assignments. The request cannot select another team or question. Extra identity fields are rejected. POST /api/submissions/{id}/confirm confirms the selected attempt. GET /api/submissions/{id} returns permitted stored text/receipt metadata, not a file or public URL.

SHA-256 is computed from canonical JSON containing the exact attempts and the chosen index; confirmation recomputes it if the selected index changes. This verifies stored content identity, not external LLM authenticity. Migration 003 retains older file-based records without deleting their objects, but the new interface requires no Storage bucket.
