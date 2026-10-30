from decimal import Decimal, InvalidOperation
import difflib
import re
from fastapi import HTTPException

RUBRICS = {
    "fix": {"target_accuracy":50,"prompt_efficiency":30,"creativity_clarity":20},
    "word_ban": {"task_accuracy":30,"banned_word_compliance":30,"prompt_effectiveness":20,"creativity":20},
    "recreate": {"target_accuracy":50,"prompt_efficiency":30,"creativity":20},
}


def checks(round_, submission):
    attempt = submission["attempts"][submission["selected_attempt"] - 1]
    answer, prompt = attempt["answer"], attempt["prompt"]
    banned = []
    matched_terms={}
    for word in round_["banned_words"]:
        variants=round_.get('banned_word_variants',{}).get(word,[word])
        alternatives=[re.escape(form.strip()).replace(r"\ ",r"\s+") for form in variants if form.strip()]
        pattern=r"(?<!\w)(?:"+'|'.join(alternatives)+r")(?!\w)"
        matches=list(re.finditer(pattern,answer.casefold(),re.IGNORECASE)) if alternatives else []
        if word.strip() and matches:
            banned.append(word)
            matched_terms[word]=sorted({match.group(0) for match in matches})
    expected = round_["expected_output"]
    return {
        "banned_matches":banned,
        "banned_matched_terms":matched_terms,
        "exact_target_match":bool(expected) and answer == expected,
        "flawed_input_literal_present":(round_['flawed_output'].strip() in prompt) if round_['kind']=='fix' else None,
        "similarity_percent":round(difflib.SequenceMatcher(None,expected,answer).ratio()*100,2) if expected else None,
        "possible_target_copy":len(expected.strip()) >= 50 and any(expected.strip().casefold() in a["prompt"].casefold() for a in submission["attempts"]),
        "attempt_count":len(submission["attempts"]),
        "note":"Similarity, missing literal context and copying flags require judge review. Direct text submissions cannot prove external LLM authenticity.",
    }


def validate_scores(kind, scores, automatic_checks):
    rubric = RUBRICS[kind]
    if set(scores) != set(rubric):
        raise HTTPException(400,"Provide exactly these score criteria: " + ", ".join(rubric))
    clean = {}
    for key, maximum in rubric.items():
        try:
            value = Decimal(str(scores[key]))
        except (InvalidOperation, ValueError):
            raise HTTPException(400,"Scores must be numbers.")
        if not value.is_finite() or not 0 <= value <= maximum or value.as_tuple().exponent < -2:
            raise HTTPException(400,f"{key} must be between 0 and {maximum}, with at most two decimal places.")
        clean[key] = float(value)
    if kind == "word_ban":
        required = 0 if automatic_checks["banned_matches"] else 30
        if clean["banned_word_compliance"] != required:
            raise HTTPException(400,f"Banned-word compliance must be {required} under the configured whole-word/phrase rule.")
    return clean, sum(Decimal(str(v)) for v in clean.values())
