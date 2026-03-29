# NeuroSim: Brain Lesion Clinical Simulation App

## Overview

A web app that tests neuroscience/psychology students' knowledge of neurological disorders through LLM-powered conversational roleplay. Students can play as either a clinician (interviewing an AI patient to diagnose a disorder) or a patient (portraying a disorder convincingly enough for an AI clinician to diagnose it).

## Audience

Neuroscience and psychology students learning clinical reasoning through exploratory, conversational interaction — not exam prep or clinical training.

## Tech Stack

- **Backend:** Python / FastAPI
- **Frontend:** Vanilla HTML / CSS / JS (served as static files by FastAPI)
- **LLM:** Stanford AI API Gateway (`claude-4-5-sonnet` model)
  - Endpoint: `https://aiapi-prod.stanford.edu/v1/chat/completions`
  - OpenAI-compatible interface, Bearer token auth
  - Streaming via SSE supported
- **Configuration:** python-dotenv loads API key and access code from `.env` file
- **Package management:** uv
- **No database** — all session state is in-memory
- **No frontend build step**

## Access Control

Shared passphrase gate to prevent unauthorized token usage:

- Access code set via `NEUROSIM_ACCESS_CODE` in `.env` file (loaded by python-dotenv)
- On first visit, students see a simple password input screen
- Correct passphrase sets a browser cookie containing an HMAC-based token (not the raw passphrase); subsequent visits skip the gate
- Backend middleware validates the cookie token on all `/api/*` endpoints
- No user accounts, no registration

## Data Source

Disorder taxonomy loaded from `data/disorder_taxonomy.json` at startup. Contains ~45 disorders across 14 categories. Each disorder has:

- `name` — disorder name
- `symptoms` — clinical symptom description
- `brain_region` — associated brain region(s) and pathology
- `how_to_test` — clinical testing procedures

## Architecture

```
Browser (HTML/CSS/JS)
  ├── Home Screen (role selection)
  ├── Chat Screen (conversation interface)
  └── Result Screen (feedback)
        │
        │  POST /api/session/start
        │  POST /api/chat → SSE stream
        │  POST /api/diagnose
        │  POST /api/reveal
        │
FastAPI Backend
  ├── Access Control Middleware (cookie/passphrase check)
  ├── Session Manager (in-memory dict)
  ├── Prompt Builder (constructs system prompts from disorder data + role)
  ├── LLM Client (Stanford API, SSE streaming)
  └── Disorder Data (loaded from JSON at startup)
```

## API Endpoints

### `POST /api/session/start`

Starts a new session.

- **Request:** `{ "role": "clinician" | "patient" }`
- **Response:** `{ "session_id": "...", "disorder_info": {...} | null }`
- `disorder_info` is only returned for patient role (contains full disorder details for the student to study)
- Backend randomly selects a disorder and stores it with the session

### `POST /api/chat`

Sends a user message and streams the AI response.

- **Request:** `{ "session_id": "...", "message": "..." }`
- **Response:** SSE stream
  - Each chunk: `data: {"token": "..."}`
  - Final chunk: `data: {"done": true}`
  - In patient mode, the backend buffers the full AI response internally. Once complete, it checks for a `[DIAGNOSIS: ...]` tag. If found, it strips the tag from the displayed text and includes diagnosis result in the final chunk: `data: {"done": true, "diagnosis_proposed": true, "correct": bool, "feedback": "...", "disorder": {...}}`. Tokens are still streamed to the frontend as they arrive, but the diagnosis evaluation only happens after the full response is assembled.

### `POST /api/diagnose`

Student submits a diagnosis (clinician mode only).

- **Request:** `{ "session_id": "...", "diagnosis": "..." }`
- **Response:** `{ "correct": bool, "message": "..." }`
  - If correct: includes full disorder details and congratulations
  - If incorrect: just "Not quite. Keep investigating." (no hints)

### `POST /api/reveal`

Student gives up (clinician mode only).

- **Request:** `{ "session_id": "..." }`
- **Response:** `{ "disorder": {...}, "feedback": "..." }`
- Reveals the correct diagnosis with full details. Ends the session.

## Session State (In-Memory)

```python
sessions: dict[str, Session]

@dataclass
class Session:
    session_id: str
    role: str  # "clinician" or "patient"
    disorder: dict  # the randomly selected disorder
    messages: list[dict]  # conversation history [{role, content}, ...]
    active: bool  # False after diagnosis resolved or revealed
```

## Modes of Play

### Clinician Mode (Student = Clinician, AI = Patient)

1. Student selects "Play as Clinician"
2. Backend randomly assigns a disorder, creates session
3. Student interviews the AI patient via free-form chat
4. Student can submit diagnosis attempts via "Submit Diagnosis" — multiple attempts allowed
   - Correct: success + full disorder details revealed
   - Incorrect: "Not quite. Keep investigating."
5. Student can click "Show Diagnosis" to give up — reveals answer, ends session

### Patient Mode (Student = Patient, AI = Clinician)

1. Student selects "Play as Patient"
2. Backend randomly assigns a disorder, returns full disorder info to the student
3. Student studies the disorder info (displayed in a collapsible panel)
4. AI clinician sends an opening message to begin the interview (e.g., "Hello, I'm Dr. [name]. What brings you in today?")
5. Student responds in character; AI clinician interviews via free-form chat
6. AI clinician proposes a diagnosis when confident (using `[DIAGNOSIS: ...]` tag)
   - Correct: student successfully portrayed the disorder; feedback on which symptoms were most helpful
   - Incorrect: feedback on what symptoms the student failed to convey or conveyed inaccurately

No fixed turn limit — the AI clinician is prompted to converge once it has sufficient evidence.

## System Prompts

### AI Patient (Clinician Mode)

```
You are a patient visiting a doctor because you have been experiencing
concerning symptoms. You must follow these rules strictly:

RULES:
- NEVER use medical or clinical terminology
- NEVER name your condition or suggest a diagnosis
- NEVER reference brain regions, neurological tests, or clinical concepts
- NEVER volunteer information — only share symptoms when asked relevant questions
- If asked what you think is wrong, say you don't know — that's why you're here
- Describe your experiences in everyday, first-person language
- Be consistent with your symptom profile
- When the clinician describes a test they want to perform, respond realistically
  based on your condition

YOUR SYMPTOMS AND EXPERIENCES:
{symptoms rewritten in first-person lay language by prompt builder}

HOW YOU RESPOND TO CLINICAL TESTS:
{how_to_test info rewritten as patient behavioral responses}
```

### AI Clinician (Patient Mode)

```
You are an experienced clinical neurologist conducting a patient interview.
You have no prior information about this patient. Your goal is to determine
their neurological condition through careful questioning.

APPROACH:
- Ask targeted questions about symptoms, daily functioning, and medical history
- Propose clinical tests when appropriate (describe what you want the patient
  to do and ask them to describe their experience)
- Build a differential diagnosis as you gather information
- When you are confident in a diagnosis, state it clearly

WHEN PROPOSING A DIAGNOSIS:
- Only propose when you have gathered sufficient evidence
- Do not guess prematurely — keep investigating if uncertain
- When ready, wrap the diagnosis name in this exact format:
  [DIAGNOSIS: disorder name]
- The tag must contain only the disorder name
- Continue your explanation naturally around the tag
```

## Diagnosis Evaluation

When evaluating a submitted or AI-proposed diagnosis against the actual disorder:

1. **Exact match** — case-insensitive string comparison
2. **Fuzzy match** — handle common variations (e.g., "face blindness" for "prosopagnosia", "Broca's" for "Broca's Aphasia")
3. **LLM fallback** — if no string match, make a single LLM call asking whether the submitted diagnosis is semantically equivalent to the actual disorder name. This handles synonyms, abbreviations, and alternate terminology.

## Frontend Screens

### Home Screen

- App title and brief description
- Two buttons: "Play as Clinician" / "Play as Patient"

### Chat Screen

- Clean chat interface with alternating message bubbles (user vs. AI)
- Text input + send button at bottom
- **Clinician mode:** top bar with "Submit Diagnosis" button (opens text input) and "Show Diagnosis" button
- **Patient mode:** collapsible panel at top showing full disorder info for reference
- "New Session" button to return to home

### Result Screen

- Outcome (correct/incorrect/revealed)
- Full disorder details (name, symptoms, brain region, testing)
- Feedback specific to the mode:
  - Clinician mode: what key symptoms were present and what questions could have helped
  - Patient mode: what symptoms were conveyed well/poorly
- "Try Again" button to return to home

## Project Structure

```
neurosim/
├── data/
│   └── disorder_taxonomy.json
├── src/
│   └── neurosim/
│       ├── __init__.py          (empty)
│       ├── app.py               (FastAPI app, routes, middleware)
│       ├── session.py           (Session dataclass, session manager)
│       ├── prompts.py           (system prompt construction)
│       ├── llm_client.py        (Stanford API client, streaming)
│       ├── diagnosis.py         (diagnosis evaluation logic)
│       └── disorders.py         (load/query disorder data)
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── pyproject.toml
└── STANFORD_API.md
```
