from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Email(Model):
    email: EmailStr


class PasswordLogin(Email):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    password: str = Field(min_length=1, max_length=200)


class VerifyOTP(Email):
    code: str = Field(pattern=r"^\d{6,10}$")


class TeamCreate(Model):
    name: str = Field(min_length=2, max_length=100)
    workstation: Literal[""] = ""  # Tracking disabled; retain legacy database compatibility.
    emails: list[EmailStr] = Field(min_length=1, max_length=2)


class StaffCreate(Email):
    role: Literal["volunteer", "judge", "organiser"]


class ParticipantImport(Model):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    csv_text: SecretStr
    email_column: str = Field(default="email", min_length=1, max_length=200)
    team_column: str = Field(default="team_name", min_length=1, max_length=200)
    password: SecretStr = SecretStr("")
    preview: bool = True


class RoundUpdate(Model):
    title: str = Field(min_length=2, max_length=160)
    task: str = Field(default="", max_length=12000)
    flawed_output: str = Field(default="", max_length=16000)
    expected_output: str = Field(default="", max_length=16000)
    banned_words: list[str] = Field(default_factory=list, max_length=50)
    duration_seconds: int = Field(ge=30, le=7200)
    upload_seconds: int = Field(ge=30, le=1800)
    qualifier_count: int = Field(ge=1, le=22)
    llm_instructions: str = Field(min_length=5, max_length=3000)


class Action(Model):
    action: Literal["brief", "start", "pause", "resume", "end_challenge", "close_uploads", "close"]


class Confirm(Model):
    selected_attempt: int = Field(ge=1, le=5)


class Attempt(Model):
    # Whitespace can be part of the target: validate without silently rewriting pasted text.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    prompt: str = Field(strict=True, min_length=1, max_length=16000)
    answer: str = Field(strict=True, min_length=1, max_length=24000)

    @field_validator("prompt", "answer")
    @classmethod
    def actual_text(cls, value):
        if not value.strip():
            raise ValueError("Enter nonempty text.")
        if "\x00" in value:
            raise ValueError("Null characters are not accepted.")
        return value


class SubmissionCreate(Model):
    attempts: list[Attempt] = Field(min_length=1, max_length=5)
    selected_attempt: int = Field(default=1, ge=1, le=5, strict=True)

    @model_validator(mode="after")
    def selected_exists(self):
        if self.selected_attempt > len(self.attempts):
            raise ValueError("Choose an attempt included in this submission.")
        return self


class Score(Model):
    scores: dict[str, Decimal]
    comments: str = Field(min_length=5, max_length=5000)
    tie_break_score: Decimal | None = Field(default=None, ge=0, le=100)
    manual_override: bool = False


class Extension(Model):
    team_id: UUID
    minutes: int = Field(ge=1, le=30)
    reason: str = Field(min_length=5, max_length=1000)


class Incident(Model):
    team_id: UUID
    round_id: UUID | None = None
    description: str = Field(min_length=5, max_length=3000)


class Disqualify(Model):
    team_id: UUID
    reason: str = Field(min_length=5, max_length=1000)


class Allocation(Model):
    workstation: Literal[""] = ""  # Tracking disabled; retain legacy database compatibility.
    reason: str = Field(min_length=5, max_length=1000)


class Reason(Model):
    reason: str = Field(min_length=5, max_length=1000)

