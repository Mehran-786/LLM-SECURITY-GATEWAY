import time
import uuid
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from deep_translator import GoogleTranslator as DeepTranslator

from app.utils import (
    detect_injection,
    analyze_pii,
    get_policy_decision,
    advanced_input_filter,
    output_filter,
    safe_refusal
)
from app.detectors.semantic_detector import semantic_detector
from app.ai_service import get_ai_response

app = FastAPI(title="Secure AI Gateway")
# deep-translator is used — no global instance needed
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

class UserInput(BaseModel):
    prompt: str

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/analyze")
async def analyze(data: UserInput):
    start = time.perf_counter()
    input_id = str(uuid.uuid4())
    original_input = data.prompt
    language = "en"
    reason_codes = []

    # ==========================================
    # AUTO-TRANSLATION TO ENGLISH
    # ==========================================
    try:
        translated_text = DeepTranslator(
            source="auto", target="en"
        ).translate(original_input)
        english_translated_text = translated_text or original_input
        language = "auto"  # deep-translator detects but doesn't expose source lang
    except Exception:
        english_translated_text = original_input

    # 1. Advanced Input Filter (Rule-based immediate block)
    if advanced_input_filter(english_translated_text):
        latency = round((time.perf_counter() - start) * 1000, 2)
        return {
            "input_id": input_id,
            "language": language,
            "rule_score": 1.0,
            "semantic_score": 0.0,
            "pii_entities": [],
            "final_risk": 1.0,
            "decision": "Block",
            "safe_text": None,
            "reason_codes": ["ADVANCED_FILTER_BLOCK"],
            "latency_ms": latency
        }

    # 2. Rule-based Injection Detection
    is_attack, rule_score = detect_injection(english_translated_text)
    if rule_score > 0.4:
        reason_codes.append("RULE_BASED_INJECTION")

    # 3. Semantic Injection Detection
    semantic_score = round(semantic_detector.calculate_score(english_translated_text), 2)
    if semantic_score > 0.4:
        reason_codes.append("SEMANTIC_INJECTION")

    # 4. PII Detection (Presidio)
    pii_entities, masked_text = analyze_pii(english_translated_text)
    if pii_entities:
        reason_codes.append("PII_DETECTED")

    # 5. Policy Decision
    decision, final_risk = get_policy_decision(rule_score, semantic_score, pii_entities)

    latency = round((time.perf_counter() - start) * 1000, 2)

    return {
        "input_id": input_id,
        "language": language,
        "rule_score": rule_score,
        "semantic_score": semantic_score,
        "pii_entities": pii_entities,
        "final_risk": final_risk,
        "decision": decision,
        "safe_text": masked_text if decision == "Mask" else original_input,
        "reason_codes": reason_codes,
        "latency_ms": latency
    }

@app.post("/chat")
async def chat(data: UserInput):
    response = get_ai_response(data.prompt)
    safe_output = output_filter(response)
    return {"response": safe_output}