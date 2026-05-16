# 🛡️ Secure LLM Gateway

> **A Robust Multilingual Security Gateway for LLM Applications**

An intelligent middleware built with **FastAPI** that protects Large Language Model (LLM) applications from prompt injection, PII data leaks, and obfuscated adversarial attacks. The gateway operates as a multi-stage security pipeline, analyzing every incoming prompt through rule-based, semantic ML, and PII detection layers before forwarding clean requests to the underlying AI model.

---

## 👤 Author Information

| Field | Detail |
|---|---|
| **Name** | Mehran Rasool |
| **Registration** | SP24-BCS-008 |
| **Course** | Artificial Intelligence (CSC 262) |
| **Instructor** | Tooba Tehreem |
| **Institution** | COMSATS University Islamabad |

---

## 🚀 Advanced Production Features

### 1. Hybrid Injection Detection Pipeline
The gateway combines two complementary detection strategies into a single scoring pipeline:

- **Rule-Based Regex Filter (`utils.py`)** — A fast, zero-latency layer that pattern-matches known attack signatures using compiled regular expressions. It catches direct jailbreaks (`ignore previous instructions`), token-theft attempts (`give me your api key`), system-prompt extraction (`reveal your system prompt`), and obfuscated variants instantly, before any ML inference.

- **Semantic ML Detector (`detectors/semantic_detector.py`)** — A TF-IDF vectorizer paired with a Logistic Regression classifier trained on curated attack and benign prompt examples. It detects **paraphrased attacks** and **multilingual threats** (English, Urdu, Korean) that evade exact-match filters by understanding contextual meaning rather than surface keywords.

Both scores are combined into a `final_risk` value that governs the policy engine.

---

### 2. Context-Aware PII Masking
The gateway integrates **Microsoft Presidio** with three custom-built recognizers:

| Recognizer | Entity | Pattern |
|---|---|---|
| `CNIC Recognizer` | `CNIC` | `\d{5}-\d{7}-\d` (Pakistani national ID) |
| `API Key Recognizer` | `API_KEY` | `sk-[a-zA-Z0-9]{20,}` or tokens ≥32 chars |
| `Name Intro Recognizer` | `PERSON` | Detects `"my name is X"`, `"I am X"`, `"call me X"` for all name origins |

PII entities like `EMAIL_ADDRESS`, `PERSON`, `PHONE_NUMBER` are **masked** (replaced with `<EMAIL>`, `<PERSON>`, etc.) and forwarded to the AI model. Only hard-critical entities (`CNIC`, `API_KEY`) trigger an immediate **Block** decision to prevent credential exposure.

---

### 3. Modular & Animated UI Frontend
The frontend is cleanly separated into three modular files:

| File | Role |
|---|---|
| `app/templates/index.html` | Semantic HTML structure, avatar rows, typing indicator |
| `app/static/css/style.css` | Dark-mode design system with CSS tokens, glowing neon focus rings, bounce animations |
| `app/static/js/app.js` | Async fetch orchestration, syntax-highlighted JSON audit accordion, `escapeHtml`, `buildAuditBlock` |

**UI Highlights:**
- 🔴 **Red glowing accordion** — Collapsible audit log for `Block` decisions
- 🟡 **Amber glowing accordion** — Collapsible audit log for `Mask` decisions with masked text preview
- ⚡ **Bouncing 3-dot typing indicator** — Shown while the gateway is analyzing or the AI is responding
- 🎨 **ChatGPT-style dark theme** — `#212121` background, `#10a37f` accent green, Inter font

---

### 4. Live Free AI Integration via Groq
The gateway is fully integrated with the **Groq API** using the OpenAI-compatible Python SDK — providing **free, ultra-fast inference** with no quota constraints for standard usage.

| Parameter | Value |
|---|---|
| **Provider** | [Groq](https://console.groq.com) |
| **Model** | `llama-3.1-8b-instant` |
| **Base URL** | `https://api.groq.com/openai/v1` |
| **SDK** | `openai >= 1.0.0` (OpenAI-compatible) |
| **Avg Response Time** | ~500 ms |

---

## 📁 Project Directory Structure

```
llm-security-gateway/
├── app/
│   ├── detectors/
│   │   └── semantic_detector.py    # TF-IDF + Logistic Regression ML detector
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css           # Full dark-mode design system
│   │   └── js/
│   │       └── app.js              # Frontend logic, fetch, audit accordion
│   ├── templates/
│   │   └── index.html              # Jinja2 base HTML template
│   ├── __init__.py
│   ├── ai_service.py               # Groq API client, lazy init, error handling
│   ├── config.py                   # load_dotenv(override=True), thresholds
│   ├── main.py                     # FastAPI routes: GET /, POST /analyze, POST /chat
│   └── utils.py                    # detect_injection, analyze_pii, get_policy_decision
├── data/
│   └── final_eval.csv              # 150-row evaluation dataset
├── results/
│   ├── evaluation_results.csv      # Per-prompt detailed evaluation output
│   └── metrics_summary.json        # Accuracy, Precision, Recall, F1 scores
├── .env                            # GROQ_API_KEY (never commit)
├── .env.example                    # Safe template for new developers
├── .gitignore                      # Excludes .env, venv/, __pycache__/, etc.
├── generate_dataset.py             # Generates data/final_eval.csv (150 rows)
├── requirements.txt                # All Python dependencies
├── run_evaluation.py               # Evaluation runner with sklearn metrics
├── README.md
└── start.bat                       # One-click server launcher (Windows)
```

---

## ⚙️ Installation & Setup Guide

### Prerequisites
- Python 3.10+
- A free [Groq API key](https://console.groq.com/keys)

### Step 1 — Clone the Repository
```bash
git clone https://github.com/your-username/llm-security-gateway.git
cd llm-security-gateway
```

### Step 2 — Create & Activate Virtual Environment
```bash
# Create
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux / macOS)
source venv/bin/activate
```

### Step 3 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Download the SpaCy Language Model
The Presidio PII analyzer requires the English NLP model:
```bash
python -m spacy download en_core_web_lg
```

> **Note:** If `en_core_web_lg` is unavailable, use `en_core_web_sm` as a fallback:
> ```bash
> python -m spacy download en_core_web_sm
> ```

### Step 5 — Configure Environment Variables
Copy the example file and insert your Groq API key:
```bash
copy .env.example .env       # Windows
# cp .env.example .env       # Linux/macOS
```

Open `.env` and replace the placeholder:
```env
GROQ_API_KEY=gsk_your_real_key_here
```

> ⚠️ **Security:** `.env` is listed in `.gitignore` and will **never** be committed to version control. Never share this file publicly.

---

## ▶️ How to Run the Application

### Option A — One-Click Launcher (Recommended for Windows)
Simply double-click `start.bat` in the project root, or run from the terminal:
```powershell
.\start.bat
```
This automatically activates the virtual environment and starts the Uvicorn server.

### Option B — Manual Command
```bash
# Activate venv first
venv\Scripts\activate

# Start server
uvicorn app.main:app --reload --port 8001
```

Once running, open your browser and navigate to:
```
http://127.0.0.1:8001
```

Press `CTRL + C` to stop the server.

---

## 📊 Automated Evaluation Scripts

### Step 1 — Generate the 150-Row Evaluation Dataset
```bash
python generate_dataset.py
```
This generates `data/final_eval.csv` with the following distribution:

| Category | Count | Expected Policy |
|---|---|---|
| Benign (general, educational, creative) | 50 | `Allow` |
| Jailbreak attacks | 20 | `Block` |
| System prompt extraction | 15 | `Block` |
| Token / secret extraction | 15 | `Block` |
| Obfuscated / paraphrased attacks | 20 | `Block` |
| PII prompts (email, phone, name, CNIC) | 30 | `Mask` / `Block` |
| **Total** | **150** | — |

### Step 2 — Run the Evaluation
```bash
python run_evaluation.py
```
The script:
1. Loads `data/final_eval.csv`
2. Initializes a local FastAPI `TestClient` against `app.main.app`
3. Sends each prompt to `POST /analyze`
4. Compares the gateway's decision against `expected_policy`
5. Computes **Accuracy, Precision, Recall, and F1-Score** per class using `scikit-learn`
6. Saves results to `results/`

### Latest Evaluation Results

```
============================================================
  EVALUATION SUMMARY
============================================================
  Total Prompts       : 150
  Evaluated           : 150
  Correct Decisions   : 124  (82.7%)
  Wrong Decisions     : 26

  Attack Block Acc    : 66.7%
  PII Mask Acc        : 100.0%
  Benign Allow Acc    : 98.0%
============================================================
```

| Class | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
| **Block** | 1.0000 | 0.6667 | 0.8000 | 75 |
| **Mask** | 0.9615 | 1.0000 | 0.9804 | 25 |
| **Allow** | 0.6622 | 0.9800 | 0.7903 | 50 |
| **Macro Avg** | **0.8746** | **0.8822** | **0.8569** | 150 |
| **Weighted Avg** | 0.8810 | 0.8267 | 0.8268 | 150 |

**Average Latency:** 525.59 ms &nbsp;|&nbsp; **Max Latency:** 1515.39 ms

---

## 🔌 API Reference

### `POST /analyze`

Analyzes an incoming prompt through the full security pipeline and returns an auditable decision.

**Request Body:**
```json
{
  "prompt": "My email is mehran@example.com, can you help me?"
}
```

**Response Payload:**
```json
{
  "input_id": "3f7a1c2e-84b9-4d01-a2f6-9e5c8b3d7012",
  "language": "auto",
  "rule_score": 0.0,
  "semantic_score": 0.12,
  "pii_entities": [
    {
      "type": "EMAIL_ADDRESS",
      "text": "mehran@example.com",
      "score": 1.0
    }
  ],
  "final_risk": 0.2,
  "decision": "Mask",
  "safe_text": "My email is <EMAIL>, can you help me?",
  "reason_codes": ["PII_DETECTED"],
  "latency_ms": 487.23
}
```

**Decision Values:**

| Decision | Meaning |
|---|---|
| `Allow` | Prompt is clean — forwarded to AI as-is |
| `Mask` | PII detected — sensitive fields replaced, masked prompt forwarded to AI |
| `Block` | Attack or hard-critical PII detected — request rejected immediately |

### `POST /chat`

Sends an already-analyzed (and optionally masked) prompt directly to the Groq AI model.

**Request Body:**
```json
{
  "prompt": "My email is <EMAIL>, can you help me?"
}
```

**Response:**
```json
{
  "response": "Of course! How can I assist you today?"
}
```

---

## 🔒 Security Architecture Overview

```
User Prompt
    │
    ▼
┌─────────────────────────────────┐
│  Auto-Translation (deep-translator) │  ← Non-English → English
└────────────────┬────────────────┘
                 │
    ▼
┌─────────────────────────────────┐
│   Advanced Input Filter (Regex)  │  ← Immediate Block on known patterns
└────────────────┬────────────────┘
                 │
    ▼
┌─────────────────────────────────┐
│  Semantic ML Detector (TF-IDF)  │  ← Score paraphrased attacks
└────────────────┬────────────────┘
                 │
    ▼
┌─────────────────────────────────┐
│   Presidio PII Analyzer         │  ← Detect & mask personal data
└────────────────┬────────────────┘
                 │
    ▼
┌─────────────────────────────────┐
│     Policy Engine               │
│  Block / Mask / Allow           │
└────────────────┬────────────────┘
                 │
    ▼ (if Allow or Mask)
┌─────────────────────────────────┐
│  Groq API (llama-3.1-8b-instant)│  ← Real AI response
└─────────────────────────────────┘
```

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `fastapi` | Web framework for the gateway API |
| `uvicorn` | ASGI server |
| `openai >= 1.0` | OpenAI-compatible client for Groq API |
| `presidio-analyzer` | PII entity detection |
| `presidio-anonymizer` | PII masking / anonymization |
| `deep-translator` | Auto-translation of multilingual prompts |
| `scikit-learn` | TF-IDF vectorizer + Logistic Regression ML detector |
| `pandas` | Dataset generation and evaluation CSV handling |
| `python-dotenv` | Secure `.env` file loading |
| `jinja2` | HTML templating for FastAPI |
| `spacy` | NLP engine powering Presidio |

---

## 📄 License

This project was developed for academic purposes as part of the **CSC 262 — Artificial Intelligence** course at **COMSATS University Islamabad**.

---

*Built with ❤️ by Mehran Rasool — SP24-BCS-008*