"""Private banks, balanced random assignments and immutable per-team question snapshots."""
import hashlib
import json
import secrets
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from fastapi import HTTPException
from .db import audit

ORIGINAL_ROUND={"recreate":1,"fix":2,"word_ban":3}
RULES={
    "recreate":"Use only the designated AI. Do not copy the target text into your prompt. No external search, secondary AI tools or assistance from other teams. Preserve the generated answer without manual editing.",
    "fix":"The original flawed response must be included as input context. Do not copy the expected answer into your prompt. Do not manually edit the AI answer. Use only the designated AI and preserve every attempt.",
    "word_ban":"Submit one final prompt and its unedited answer. Banned words are checked case-insensitively, including the published singular/plural variants. A banned match earns zero for the compliance criterion, not an automatic zero for the whole challenge. Only whole words/phrases match; unrelated substrings do not.",
}


class QuestionData(BaseModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=False)
    key: str = Field(pattern=r"^(recreate|fix|word_ban)-\d{2,4}$")
    kind: Literal['fix','word_ban','recreate']
    original_round: int = Field(ge=1,le=3)
    source_number: int = Field(ge=1,le=9999)
    title: str = Field(min_length=1,max_length=200)
    task: str = Field(min_length=1,max_length=12000)
    flawed_output: str = Field(default="",max_length=16000)
    expected_output: str = Field(default="",max_length=16000)
    banned_words: list[str] = Field(default_factory=list,max_length=50)
    judge_notes: str = Field(default="",max_length=6000)

    @model_validator(mode="after")
    def coherent_question(self):
        if self.original_round!=ORIGINAL_ROUND[self.kind] or self.key!=f"{self.kind}-{self.source_number:02}":
            raise ValueError("Question key, original round and challenge kind must agree.")
        if not self.task.strip() or not self.title.strip():
            raise ValueError("A question needs a title and task.")
        if self.kind in ('fix','recreate') and not self.expected_output.strip():
            raise ValueError("Fix/Recreate questions need an exact reference target.")
        if self.kind=='fix' and not self.flawed_output.strip():
            raise ValueError("Fix questions need a flawed response.")
        if self.kind=='word_ban' and not self.banned_words:
            raise ValueError("Word Ban questions need banned words.")
        if any(not word.strip() or len(word)>80 for word in self.banned_words):
            raise ValueError("Banned words/phrases must contain 1–80 characters.")
        return self


def plural_variants(word):
    # These explicit forms are published to teams and frozen with each assignment.
    lower=word.casefold().strip()
    irregular={"leaf":{"leaf","leaves"},"leaves":{"leaf","leaves"},
               "fangs":{"fang","fangs"},"colors":{"color","colors"},
               "money":{"money","monies","moneys"},"physics":{"physics"},"photosynthesis":{"photosynthesis"}}
    if lower in irregular:
        return sorted(irregular[lower])
    if len(lower)>1 and lower.endswith('y') and lower[-2] not in 'aeiou':
        return sorted({lower,lower[:-1]+'ies'})
    return sorted({lower,lower+('es' if lower.endswith(('s','x','z','ch','sh')) else 's')})


def prepare_bank(raw):
    if not isinstance(raw,dict) or raw.get('format_version')!=1 or not isinstance(raw.get('questions'),list) or not raw['questions']:
        raise ValueError("Expected format_version 1 and a nonempty questions array.")
    output=[]
    keys=set()
    for item in raw['questions']:
        data=QuestionData.model_validate(item).model_dump()
        if data['key'] in keys:
            raise ValueError("Duplicate question key: "+data['key'])
        keys.add(data['key'])
        data['source_file']=f"round_{data['original_round']}_question_bank.md"
        data['participant_rules']=RULES[data['kind']]
        data['banned_word_variants']={word:plural_variants(word) for word in data['banned_words']}
        canonical=json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        data['content_hash']=hashlib.sha256(canonical).hexdigest()
        output.append(data)
    return output


def bank_count(conn, kind):
    return conn.execute("SELECT count(*) AS n FROM question_bank WHERE kind=%s AND active",(kind,)).fetchone()['n']


def assign(conn, round_, actor):
    # The caller holds the round lock and the competition lifecycle advisory lock.
    if conn.execute("SELECT 1 FROM question_assignments WHERE round_id=%s",(round_['id'],)).fetchone():
        raise HTTPException(409,"This round already has question assignments. They cannot be rerolled.")
    teams=conn.execute("SELECT team_id FROM entries WHERE round_id=%s AND outcome='eligible' ORDER BY team_id FOR UPDATE",(round_['id'],)).fetchall()
    pool=conn.execute("SELECT * FROM question_bank WHERE kind=%s AND active ORDER BY key FOR SHARE",(round_['kind'],)).fetchall()
    if not teams or not pool:
        raise HTTPException(409,"Import an active question bank and enrol eligible teams before starting.")
    for question in pool:
        if not question['task'].strip() or (question['kind'] in ('fix','recreate') and not question['expected_output'].strip()) or (question['kind']=='fix' and not question['flawed_output'].strip()) or (question['kind']=='word_ban' and not question['banned_words']):
            raise HTTPException(409,"The active question bank contains incomplete material. Review it before starting.")
    rng=secrets.SystemRandom()
    rng.shuffle(teams)
    choices=[]
    while len(choices)<len(teams):
        cycle=list(pool)
        rng.shuffle(cycle)
        choices.extend(cycle[:len(teams)-len(choices)])
    for team,question in zip(teams,choices):
        snapshot={key:question[key] for key in ('key','kind','original_round','source_number','source_file','title','task','flawed_output','expected_output','banned_words','banned_word_variants','participant_rules','judge_notes','content_hash')}
        conn.execute("INSERT INTO question_assignments(round_id,team_id,question_id,snapshot,assigned_by) VALUES (%s,%s,%s,%s::jsonb,%s)",
                     (round_['id'],team['team_id'],question['id'],json.dumps(snapshot,ensure_ascii=False),actor))
    audit(conn,actor,'assign_random_questions',{'round_id':round_['id'],'teams':len(teams),'bank_size':len(pool),'policy':'balanced shuffled cycles without replacement inside each cycle'})


def for_team(conn, round_, team_id):
    assignment=conn.execute("SELECT * FROM question_assignments WHERE round_id=%s AND team_id=%s",(round_['id'],team_id)).fetchone()
    if not assignment:
        raise HTTPException(409,"No question is assigned to this team. The organiser must start the round first.")
    snapshot=assignment['snapshot']
    if snapshot['kind']!=round_['kind']:
        raise HTTPException(409,"Question assignment does not match this round. Contact the organiser.")
    merged=dict(round_)
    merged.update({key:snapshot[key] for key in ('task','flawed_output','expected_output','banned_words','banned_word_variants','participant_rules','judge_notes')})
    if round_['task'].strip():
        merged['task']+='\n\nAdditional round instructions:\n'+round_['task']
    merged.update(question_id=assignment['question_id'],assignment_id=assignment['id'],question_key=snapshot['key'],
                  question_title=snapshot['title'],original_round=snapshot['original_round'],question_hash=snapshot['content_hash'])
    return merged


def display_context(round_, private=False):
    fields=('task','flawed_output','expected_output','banned_words','banned_word_variants','participant_rules',
            'question_key','question_title','question_id','assignment_id','question_hash','original_round')
    data={key:round_.get(key) for key in fields}
    if round_['kind']=='word_ban' and not private:
        data['expected_output']=''
    if private:
        data['judge_notes']=round_.get('judge_notes','')
    return data


def for_submission(conn, round_, submission):
    context=for_team(conn,round_,submission['team_id'])
    if submission.get('assignment_id')!=context['assignment_id']:
        raise HTTPException(409,"This submission is not linked to the team's assigned question. Do not import a new bank into an already-running legacy competition.")
    return context

