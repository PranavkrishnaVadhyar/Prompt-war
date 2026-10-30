-- Non-destructive upgrade from file uploads to direct prompt/answer entry.
BEGIN;
SET LOCAL search_path TO prompt_war;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='prompt_war' AND table_name='submissions' AND column_name='uploaded_by')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='prompt_war' AND table_name='submissions' AND column_name='submitted_by') THEN
        ALTER TABLE submissions RENAME COLUMN uploaded_by TO submitted_by;
    END IF;
END $$;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS source_type text NOT NULL DEFAULT 'file_legacy'
    CHECK(source_type IN ('direct','file_legacy'));
ALTER TABLE submissions ALTER COLUMN filename DROP NOT NULL;
ALTER TABLE submissions ALTER COLUMN storage_path DROP NOT NULL;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='direct_submission_has_no_file' AND conrelid='prompt_war.submissions'::regclass) THEN
        ALTER TABLE submissions ADD CONSTRAINT direct_submission_has_no_file
            CHECK(source_type<>'direct' OR (filename IS NULL AND storage_path IS NULL));
    END IF;
END $$;
-- Existing parsed submissions, receipts, model runs and private objects are retained.
-- No table, file or bucket is deleted. New writes explicitly use source_type='direct'.
COMMIT;
