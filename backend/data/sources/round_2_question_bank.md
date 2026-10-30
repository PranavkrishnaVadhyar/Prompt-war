# VYUHAM '26 | PROMPT WAR

## Round 2 Question Bank: Fix the Output

**Time Limit:** 10 Minutes
**Max Attempts:** 5
**Total Marks:** 100

---

### Operational Overview & Rules

* **Objective:** Correct an incorrect or poorly generated AI response to match the expected target output.
* **Key Restrictions:**
  * The original incorrect response MUST be used as input context.
  * Directly copying the target answer into the prompt is strictly prohibited.
  * Manual editing of AI-generated outputs is not allowed.
* **Evaluation (100 Marks):** Target Accuracy (50) | Prompt Efficiency (30) | Creativity & Clarity (20).

---

### Challenge 1: The Unprofessional Admin

**Flawed Input:**
```text
yo so the server crashed at 03:00 lol. it was a memory leak or whatever. we rebooted it. peace.
```

**Expected Target:**
```text
[INCIDENT 03:00]
Cause: Memory Leak
Status: Rebooted
```

**Description:**
The AI generated a highly unprofessional and unstructured incident report. Engineer a prompt to strip all conversational slang, enforce a strict bracketed timestamp prefix, and format the core facts without hallucinating any new technical details.

---

### Challenge 2: The Verbose Coder

**Flawed Input:**
```text
Here is the python code to add two numbers.
```python
def add(a, b):
    return a + b
```
This function takes two arguments...
```

**Expected Target:**
```python
lambda a, b: a + b
```

**Description:**
The AI over-explained a simple coding task and used standard function syntax inside code blocks. Instruct the AI to rewrite the logic as a single-line Python lambda expression, explicitly forbidding Markdown code blocks and any conversational text.

---

### Challenge 3: The Tangled Data

**Flawed Input:**
```text
Employee John Doe is 28 years old and works in the IT department. His ID number is 9942.
```

**Expected Target:**
```json
{
  "id": 9942,
  "name": "John Doe",
  "dept": "IT",
  "age": 28
}
```

**Description:**
Conversational text contains employee data. Prompt the AI to extract it into a flat JSON object, strictly mapping keys (e.g., "department" to "dept") and ensuring ID and age are cast as integers rather than strings.

---

### Challenge 4: The Stubborn Markdown

**Flawed Input:**
```text
Item: Laptop, Price: 1200, Stock: 5. Item: Mouse, Price: 25, Stock: 50.
```

**Expected Target:**
```markdown
| Item | Price | Stock |
|---|---|---|
| Laptop | $1200 | 5 |
| Mouse | $25 | 50 |
```

**Description:**
The AI provided inventory data as an unreadable linear string. Force it to convert this strictly into a 3x3 Markdown table and dynamically inject a dollar sign (`$`) before the values in the Price column.

---

### Challenge 5: The Accidental Haiku

**Flawed Input:**
```text
The sky is very dark tonight. The stars are shining bright. The moon is full and beautiful.
```

**Expected Target:**
```text
Dark sky shines tonight
Stars are glowing very bright
Full moon beautiful
```

**Description:**
The AI generated basic prose describing the night sky. Constrain it to convert this exact imagery into a strict 5-7-5 syllable haiku format without adding new concepts, removing punctuation, and enforcing Title Case on the first letter of each line.

---

### Challenge 6: The Blunt Rejection

**Flawed Input:**
```text
We reject your application because you have no experience.
```

**Expected Target:**
```text
Thank you for applying. While we require more experience at this time, we encourage future applications.
```

**Description:**
The AI generated a harsh rejection letter. Shift the tone to positive, corporate, and encouraging while keeping the core reason (lack of experience) intact. An exact wording match is required to prevent a multi-paragraph email.

---

### Challenge 7: The Misaligned List

**Flawed Input:**
```text
1. apples.
2. Bananas
3- orange.
```

**Expected Target:**
```markdown
- Apples
- Bananas
- Oranges
```

**Description:**
The AI generated a messy list with mixed punctuation, inconsistent casing, and numbers instead of bullets. Enforce standard Markdown bullets (`-`), capitalize the first letter of every item, make them plural, and remove all numbers and trailing periods.

---

### Challenge 8: The Leaky Prompt

**Flawed Input:**
```text
Sure, I can help you translate that to French. The translation of 'Hello world' is 'Bonjour le monde'.
```

**Expected Target:**
```text
Bonjour le monde
```

**Description:**
The AI included conversational filler before providing the requested translation. Force it to output *only* the translated phrase without quotation marks, pleasantries, or acknowledging the prompt.

---

### Challenge 9: The Chatty Log

**Flawed Input:**
```text
Attention team! It seems the database failed to connect at 10:45 AM today. The system error code was 502.
```

**Expected Target:**
```text
[10:45 AM] ERROR 502: Database Connection Failed
```

**Description:**
The AI generated a conversational system alert. Condense it into a strict single-line system log format using brackets for the timestamp and full capitalization for the error type, stripping all conversational text.

---

### Challenge 10: The Overenthusiastic Marketer

**Flawed Input:**
```text
You are going to love our new SuperPhone! It has an incredible 6-inch screen, unbelievable 128GB of storage, and taking pictures is amazing with its 12MP camera! Order yours today!
```

**Expected Target:**
```text
The SuperPhone features a 6-inch screen, 128GB of storage, and a 12MP camera.
```

**Description:**
The AI wrote a hyper-emotional marketing pitch. Strip out all exclamation points, marketing buzzwords, and emotional adjectives, reducing the text to a single, dry, objective sentence listing the three technical specs.

---

### Challenge 11: The Messy Citation

**Flawed Input:**
```text
You should really read The Great Gatsby by F. Scott Fitzgerald. It is a classic that was published in 1925 by Charles Scribner's Sons.
```

**Expected Target:**
```markdown
Fitzgerald, F. S. (1925). *The Great Gatsby*. Charles Scribner's Sons.
```

**Description:**
The AI gave a book recommendation conversationally. Extract the data into a rigid APA-style citation: initial the first name, place the year in parentheses, and italicize the book title using Markdown.