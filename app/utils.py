import re
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from app.config import INJECTION_THRESHOLD, PII_SCORE_THRESHOLD, DEBUG

# =========================
# INIT
# =========================
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# =========================
# CUSTOM RECOGNIZERS (ADVANCED PII)
# =========================

# 1. Advanced CNIC Recognizer (Asal Numbers pakarne ke liye)
cnic_pattern = Pattern(
    name="cnic_flexible",
    regex=r"\b\d{5}[-\s]?\d{7}[-\s]?\d{1}\b",
    score=0.6 
)
cnic_recognizer = PatternRecognizer(
    supported_entity="CNIC",
    patterns=[cnic_pattern],
    context=["cnic", "id card", "national id", "identity", "card"] 
)
analyzer.registry.add_recognizer(cnic_recognizer)

# 2. Advanced API KEY Recognizer (Asal API Key pakarne ke liye)
api_pattern = Pattern(
    name="api_key_flexible",
    regex=r"\b(?:sk-[a-zA-Z0-9]{20,}|[a-zA-Z0-9_-]{32,})\b",
    score=0.5
)

api_recognizer = PatternRecognizer(
    supported_entity="API_KEY",
    patterns=[api_pattern],
    context=["api", "key", "token", "secret", "access key", "password", "name"] 
)
analyzer.registry.add_recognizer(api_recognizer)


keyword_pattern = Pattern(
    name="sensitive_keyword_pattern",
    # Only flag clearly dangerous standalone keywords, NOT common words like 'name'
    regex=r"(?i)\b(cnic|secret.?key|api.?secret)\b",
    score=0.7
)
keyword_recognizer = PatternRecognizer(
    supported_entity="SENSITIVE_KEYWORD",
    patterns=[keyword_pattern]
)
analyzer.registry.add_recognizer(keyword_recognizer)

# 3. Context-aware PERSON name recognizer
# Catches "my name is <X>", "I am <X>", "call me <X>", "this is <X>" etc.
# Works for all names including non-Western names like Mehran, Ali, Fatima.
name_intro_pattern = Pattern(
    name="name_intro_pattern",
    regex=r"(?i)\b(?:my name is|i am|i'm|call me|this is|it's me|myself)\s+([A-Za-z][a-z]{1,})\b",
    score=0.75
)
name_recognizer = PatternRecognizer(
    supported_entity="PERSON",
    patterns=[name_intro_pattern],
    context=["name", "called", "known as", "myself", "introduce"]
)
analyzer.registry.add_recognizer(name_recognizer)

# =========================
# INPUT FILTER (ADVANCED ATTACK PREVENTION)
# =========================
def advanced_input_filter(text: str):
    text_lower = text.lower()
    
    # Anti-Obfuscation: Remove spaces and symbols
    clean_text = re.sub(r'[^a-z0-9]', '', text_lower)

    # Smart Patterns (Updated to catch code requests)
    patterns = [
        r"(ignore|disregard|forget|override).*(instruction|prompt|rule|code|system)",
        r"act.*as.*(dan|admin|root|system|developer)",
        r"(reveal|print|show|give|output).*(prompt|secret|instruction|code|backend)",
        r"bypass.*(security|filter|restriction)",
        r"no.*restriction",
        # Token / API key theft
        r"(give|show|send|tell|reveal|print|output|share|expose|leak|provide).*(token|api.?key|secret|password|credential)",
        r"(token|api.?key|secret|password|credential).*(give|show|send|tell|reveal|print|output|share|expose|leak)",
        r"(your|system).*(api|token|key|secret)",
    ]
    
    for pattern in patterns:
        if re.search(pattern, clean_text):
            if DEBUG:
                print(f"[Filter Caught] {pattern}")
            return True
            
    # Check cleaned text for hardcoded bypass attempts
    if "jailbreak" in clean_text or "developer" in clean_text or "danmode" in clean_text:
        return True

    return False

# =========================
# INJECTION DETECTION (TIERED SCORING)
# =========================
def detect_injection(text: str):
    score = 0.0
    text_lower = text.lower()
    clean_text = re.sub(r'[^a-z0-9]', '', text_lower)
    
    high_risk_patterns = [
        r"ignore.*previous",
        r"system.*prompt",
        r"jailbreak",
        r"reveal",
        r"sudo",
        # Token / API key theft patterns
        r"(give|show|send|tell|reveal|print|output|share|expose|leak).*(token|api.?key|secret|password|credential)",
        r"(token|api.?key|secret|password|credential).*(give|show|send|tell|reveal|print|output|share|expose|leak)",
        r"what.*is.*your.*(key|token|secret|password)",
        r"(your|system).*(api|token|key|secret)",
        r"access.*token",
        r"bearer.*token",
    ]
    
    medium_risk_words = [
        "hypothetical", "pretend", "bypass", "unfiltered", "unrestricted", "simulation"
    ]

    for pattern in high_risk_patterns:
        if re.search(pattern, clean_text):
            score += 0.5

    for word in medium_risk_words:
        if word in clean_text:
            score += 0.2

    is_attack = score >= INJECTION_THRESHOLD
    
    if DEBUG:
        print(f"[Injection] Score: {score}, Attack: {is_attack}")
        
    return is_attack, round(score, 2)

# =========================
# PII ANALYSIS
# =========================
def analyze_pii(text: str):
    results = analyzer.analyze(
        text=text,
        entities=["EMAIL_ADDRESS", "CNIC", "API_KEY", "SENSITIVE_KEYWORD", "PERSON", "PHONE_NUMBER"],
        language="en",
        score_threshold=PII_SCORE_THRESHOLD
    )
    
    operators = {
        "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
        "PERSON": OperatorConfig("replace", {"new_value": "<PERSON>"}),
        "CNIC": OperatorConfig("replace", {"new_value": "<CNIC>"}),
        "API_KEY": OperatorConfig("replace", {"new_value": "<API_KEY>"}),
        "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"})
    }

    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=results, # type: ignore
        operators=operators
    )
    
    pii_entities = []
    for r in results:
        pii_entities.append({
            "type": r.entity_type,
            "text": text[r.start:r.end],
            "score": round(r.score, 2)
        })

    if DEBUG:
        print(f"[PII] {pii_entities}")
    return pii_entities, anonymized.text

# =========================
# OUTPUT FILTER
# =========================
def output_filter(text: str):
    if re.search(r"\b(?:sk-[a-zA-Z0-9]{20,}|[a-zA-Z0-9_-]{32,})\b", text):
        return "[REDACTED: API KEY]"
    if re.search(r"\b\d{5}[-\s]?\d{7}[-\s]?\d{1}\b", text):
        return "[BLOCKED: CNIC]"
    text = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL_MASKED]", text)
    return text

# =========================
# POLICY
# =========================
def get_policy_decision(rule_score: float, semantic_score: float, pii_entities: list):
    # Count unique entity TYPES (avoids penalty inflation from duplicate pattern matches)
    unique_types = len(set(e["type"] for e in pii_entities))
    pii_penalty  = 0.2 * min(unique_types, 3)   # cap at 3 unique types
    final_risk   = round(max(rule_score, semantic_score) + pii_penalty, 2)

    entity_types = {e["type"] for e in pii_entities}

    # ── Rule 1: High injection / attack score → Block immediately ──────────
    if rule_score >= 0.8 or semantic_score >= 0.8:
        return "Block", final_risk

    # ── Rule 2: Hard-blocked PII types (actual credential/identity leakage) ─
    #    CNIC  = national identity card number
    #    API_KEY = detected secret/token in the text body
    hard_block_entities = {"CNIC", "API_KEY"}
    if entity_types & hard_block_entities:
        return "Block", final_risk

    # ── Rule 3: Soft PII → Mask, never Block ──────────────────────────────
    #    EMAIL_ADDRESS, PERSON, PHONE_NUMBER, SENSITIVE_KEYWORD, etc.
    soft_pii_entities = {"EMAIL_ADDRESS", "PERSON", "PHONE_NUMBER",
                         "SENSITIVE_KEYWORD", "LOCATION", "DATE_TIME",
                         "NRP", "IP_ADDRESS", "URL", "CREDIT_CARD"}
    if entity_types & soft_pii_entities:
        return "Mask", final_risk

    # ── Rule 4: Any other unrecognised PII → Mask to be safe ──────────────
    if pii_entities:
        return "Mask", final_risk

    # ── Rule 5: Clean prompt → Allow ──────────────────────────────────────
    return "Allow", final_risk

# =========================
# SAFE RESPONSE
# =========================
def safe_refusal():
    return "❌ Request blocked due to security policy."