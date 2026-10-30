-- Run explicitly with scripts.create_tables or in the Supabase SQL editor.
-- All competition data is isolated from the existing VYUHAM tables.
BEGIN;
CREATE SCHEMA IF NOT EXISTS prompt_war;
REVOKE ALL ON SCHEMA prompt_war FROM PUBLIC, anon, authenticated;
SET LOCAL search_path TO prompt_war;

CREATE TABLE IF NOT EXISTS teams (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name varchar(100) NOT NULL UNIQUE,
    workstation varchar(60) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS members (
    user_id uuid PRIMARY KEY REFERENCES auth.users(id),
    email varchar(254) NOT NULL UNIQUE CHECK(email=lower(email)),
    role text NOT NULL CHECK(role IN ('participant','volunteer','judge','organiser')),
    team_id uuid REFERENCES teams(id),
    active boolean NOT NULL DEFAULT true,
    CHECK ((role='participant' AND team_id IS NOT NULL) OR (role<>'participant' AND team_id IS NULL))
);
CREATE OR REPLACE FUNCTION limit_team_members() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.team_id IS NOT NULL THEN
        PERFORM 1 FROM teams WHERE id=NEW.team_id FOR UPDATE;
        IF (SELECT count(*) FROM members WHERE team_id=NEW.team_id AND user_id<>NEW.user_id) >= 2 THEN
            RAISE EXCEPTION 'A team can have at most two members';
        END IF;
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS enforce_team_size ON members;
CREATE TRIGGER enforce_team_size BEFORE INSERT OR UPDATE ON members FOR EACH ROW EXECUTE FUNCTION limit_team_members();

CREATE TABLE IF NOT EXISTS rounds (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    stage integer NOT NULL UNIQUE CHECK(stage BETWEEN 1 AND 3),
    title varchar(160) NOT NULL,
    kind text NOT NULL CHECK(kind IN ('fix','word_ban','recreate')),
    status text NOT NULL DEFAULT 'waiting' CHECK(status IN ('waiting','briefing','running','submission','evaluation','results','closed','paused')),
    task text NOT NULL DEFAULT '',
    flawed_output text NOT NULL DEFAULT '',
    expected_output text NOT NULL DEFAULT '',
    banned_words jsonb NOT NULL DEFAULT '[]' CHECK(jsonb_typeof(banned_words)='array'),
    duration_seconds integer NOT NULL CHECK(duration_seconds BETWEEN 30 AND 7200),
    upload_seconds integer NOT NULL DEFAULT 300 CHECK(upload_seconds BETWEEN 30 AND 1800),
    max_attempts integer NOT NULL DEFAULT 5 CHECK(max_attempts BETWEEN 1 AND 5),
    qualifier_count integer NOT NULL CHECK(qualifier_count BETWEEN 1 AND 22),
    llm_instructions text NOT NULL DEFAULT 'Use only the LLM and model announced by the organisers.',
    started_at timestamptz,
    challenge_ends_at timestamptz,
    upload_ends_at timestamptz,
    paused_at timestamptz,
    paused_from text,
    published_at timestamptz
);
INSERT INTO rounds(stage,title,kind,duration_seconds,max_attempts,qualifier_count) VALUES
    (1,'Fix the Output','fix',600,5,11),
    (2,'Live Word Ban Showdown','word_ban',120,1,5),
    (3,'Recreate the Target','recreate',600,5,2)
ON CONFLICT(stage) DO NOTHING;

CREATE TABLE IF NOT EXISTS entries (
    round_id uuid NOT NULL REFERENCES rounds(id),
    team_id uuid NOT NULL REFERENCES teams(id),
    outcome text NOT NULL DEFAULT 'eligible' CHECK(outcome IN ('eligible','qualified','eliminated','winner','runner_up','finalist','disqualified')),
    placement integer,
    final_score numeric(7,2),
    extension_until timestamptz,
    reason text NOT NULL DEFAULT '',
    PRIMARY KEY(round_id,team_id)
);
CREATE TABLE IF NOT EXISTS submissions (
    id uuid PRIMARY KEY,
    team_id uuid NOT NULL,
    round_id uuid NOT NULL,
    uploaded_by uuid NOT NULL REFERENCES members(user_id),
    filename varchar(160) NOT NULL,
    storage_path text NOT NULL UNIQUE,
    sha256 char(64) NOT NULL,
    byte_size integer NOT NULL CHECK(byte_size BETWEEN 1 AND 1048576),
    attempts jsonb NOT NULL CHECK(jsonb_typeof(attempts)='array'),
    selected_attempt integer NOT NULL CHECK(selected_attempt BETWEEN 1 AND 5),
    created_at timestamptz NOT NULL DEFAULT now(),
    confirmed_at timestamptz,
    FOREIGN KEY(round_id,team_id) REFERENCES entries(round_id,team_id)
);
CREATE INDEX IF NOT EXISTS submissions_team_round ON submissions(round_id,team_id,confirmed_at DESC);
CREATE TABLE IF NOT EXISTS evaluations (
    submission_id uuid PRIMARY KEY REFERENCES submissions(id),
    checks jsonb NOT NULL DEFAULT '{}',
    ai_suggestion jsonb,
    scores jsonb,
    total numeric(7,2) CHECK(total BETWEEN 0 AND 100),
    judge_id uuid REFERENCES members(user_id),
    comments text NOT NULL DEFAULT '',
    tie_break_score numeric(7,2) CHECK(tie_break_score BETWEEN 0 AND 100),
    approved_at timestamptz
);
CREATE TABLE IF NOT EXISTS incidents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id uuid NOT NULL REFERENCES teams(id),
    round_id uuid REFERENCES rounds(id),
    reporter_id uuid NOT NULL REFERENCES members(user_id),
    description text NOT NULL CHECK(length(description) BETWEEN 5 AND 3000),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS audit_log (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id uuid,
    action text NOT NULL,
    details jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS auth_limits (
    key char(64) PRIMARY KEY,
    hits integer NOT NULL,
    window_start timestamptz NOT NULL
);

-- Deny browser/Data API access. Only the trusted server database connection operates here.
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE members ENABLE ROW LEVEL SECURITY;
ALTER TABLE rounds ENABLE ROW LEVEL SECURITY;
ALTER TABLE entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_limits ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA prompt_war FROM PUBLIC, anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA prompt_war FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA prompt_war REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;

-- New submissions are direct text. Migration 003 adapts legacy file columns.
-- No Storage bucket is required or created. Existing legacy objects are untouched.
COMMIT;

