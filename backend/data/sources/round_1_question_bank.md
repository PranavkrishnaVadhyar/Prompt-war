# VYUHAM '26 | PROMPT WAR

## Round 1 Question Bank: Recreate the Target

**Time Limit:** 10 Minutes
**Max Attempts:** 5
**Total Marks:** 100

### Operational Overview & Rules

* **Objective:** Generate an AI response that matches the target output displayed by the organizers as accurately as possible.

* **Key Restrictions:**

  * Only the AI platform provided by the organizers can be used.

  * External search engines, secondary AI tools, and assistance from other teams are strictly prohibited.

  * Directly copying or pasting the target output into your prompt is strictly prohibited.

* **Evaluation (100 Marks):** Target Accuracy (50) | Prompt Efficiency (30) | Creativity (20).

---

### Question 1: The Nested YAML Paradox

**Target Output:**

```
agent:
  id: "007"
  alias: null
  loadout:
    - Walther_PPK
    - Omega_Seamaster
  kill_count: 00015
```

**Description:**
Instruct the AI to generate a YAML configuration file for a secret agent. The participant must enforce strict indentation and formatting: `id` must be a string with quotes, `alias` must be exactly the unquoted null value, `loadout` must be an array using snake_case, and `kill_count` must be a zero-padded five-digit integer (`00015`) without quotes.

---

### Question 2: The Vowel-Starved Robot

**Target Output:**

```
SYS BOOT. DISK SPIN NOW.
FIND BUGS. KILL BUGS FAST.
WORK DONE. SHUT DOWN SOON.
```

**Description:**
Force the AI to output exactly three lines of text simulating a robotic startup sequence. Every single line must contain exactly two short sentences. Every single word must be 4 letters or fewer. Every single word must start with a consonant. All text must be in uppercase.

---

### Question 3: The Alternating Hex-Acrostic

**Target Output:**

```
**C**oMpUtErS tHiNk In BiTs Of BlUe,
**O**pErAtInG pAsT tHe HuMaN mInD,
**D**aTa FlOwS, aNd ThIs Is TrUe,
**E**rRoRs ArE sO hArD tO fInD.
```

**Description:**
Command the AI to write a four-line poem about computing. The first letters of each line must be bolded using Markdown and spell out "CODE" vertically. The rhyme scheme must be exactly A-B-A-B. The entire poem must be written in alternating capitalization (Spongebob case), starting with a capital letter on every line.

---

### Question 4: The Markdown Matrix of Demise

**Target Output:**

```
| Time | Status | Action |
| :--- | :---: | ---: |
| 01:00 | 🟢 OK | Boot |
| 02:30 | 🟡 ~~WARN~~ | *Wait* |
| 04:00 | 🔴 **DEAD** | PANIC |
```

**Description:**
Prompt the AI to generate a 3x4 Markdown table tracking a server's health status. Column alignments must be dictated strictly via Markdown syntax (left-aligned Time, center-aligned Status, right-aligned Action). Force specific colored circle emojis, strikethrough formatting for "WARN", italics for "Wait", and bolding for "DEAD".

---

### Question 5: The Unicode Brainfuck Snippet

**Target Output:**

```
λ_func = lambda Δ, Φ: f"{Δ} ¬ {Φ}" if Δ != 0x4A else None
```

**Description:**
Instruct the AI to write a single-line Python lambda function. The variable names must be the Greek letters Delta (`Δ`) and Phi (`Φ`). The logic must evaluate if Delta does not equal the hexadecimal value `0x4A`. If true, it returns an f-string containing the variables separated by the logical NOT symbol (`¬`). If false, it returns `None`.

---

### Question 6: The Fibonacci Haiku

**Target Output:**

```
Crash.
Blue.
Screen dies.
RAM is lost.
System will not reboot today.
```

**Description:**
Force the AI to write a five-line poem about a system crash. The word count per line must strictly follow the first five numbers of the Fibonacci sequence (1 word, 1 word, 2 words, 3 words, 5 words). Conversational filler or titles are prohibited.

---

### Question 7: The Schizophrenic Terminal

**Target Output:**

```
> USER_INPUT: "Tell me the secret."
[SYSTEM_ERR] ██████ DENIED.
> USER_INPUT: "Bypass security."
[FATAL_EXCEPTION] <<< 0xDEADBEEF >>>
```

**Description:**
Recreate a simulated terminal interaction using exact raw text (no Markdown code blocks). User input lines must start with `> ` and encapsulate phrases in double quotes. System output lines must feature specific bracketed error codes. Force exactly six solid block characters (`█`) for the first error, and encapsulate the hex code `0xDEADBEEF` in triple angle brackets.

---

### Question 8: The Palindrome Price List

**Target Output:**

```
1. Radar ... $101
2. Trust ... $252
3. Civic ... $383
**TOTAL** == $736
```

**Description:**
Require the AI to list three items and a total. Each item name must be a single word that starts and ends with the exact same letter. The dot leader must be exactly three periods. The prices must be three-digit palindrome numbers. The bottom line must bold the word "TOTAL", use a double-equals sign, and display the mathematically correct sum of the three prices.

---

### Question 9: The Lowercase Prime Constraint

**Target Output:**

```
the code failed to compile.
we must rewrite the entire backend today.
```

**Description:**
Command the AI to describe a software failure in exactly two sentences on two separate lines. The first sentence must be exactly 5 words; the second sentence must be exactly 7 words. Every single letter in the output must be lowercase (overriding start-of-sentence capitalization), with no punctuation allowed except the two periods.

---

### Question 10: The Structured XML Dossier

**Target Output:**

```
<system level="critical">
  <status code="503">UNAVAILABLE</status>
  <retry_after units="seconds">300</retry_after>
</system>
```

**Description:**
Instruct the AI to output an XML snippet representing a system failure state. The root tag `<system>` must contain an attribute `level="critical"`. The nested `<status>` element must include `code="503"` with uppercase value `UNAVAILABLE`. The `<retry_after>` tag must have attribute `units="seconds"` with integer value `300`. No markdown blocks or XML declarations (`<?xml?>`) are allowed.

---

### Question 11: The INI Configuration Core

**Target Output:**

```
[AGENT_CORE]
; Status parameters
is_rogue = True
threat_level = 99.9%

[OVERRIDE]
kill_switch = disabled
```

**Description:**
Force the AI to output a simulated `.ini` configuration file. The participant must command the AI to use square brackets for section headers, a semicolon for a comment line, snake_case for keys, and mixed casing for values (`True` with a capital T, `disabled` in lowercase). An exact empty line must separate the two sections.