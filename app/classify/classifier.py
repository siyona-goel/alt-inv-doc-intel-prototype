# app/classify/classifier.py
import os
import re
from .ai_classifier import classify_text_ai

DOC_TYPES = {
    "capital_call_letter": [
        "capital call", "drawdown notice", "capital contribution", "drawdown",
        "funding notice", "call notice", "capital call request", "capital call notice"
    ],
    "distribution_notice": [
        "distribution", "dividend", "distribution notice", "distribution payment",
        "fund distributions", "annual distributions"
    ],
    "valuation_reports": [
        "valuation", "valuation report", "valuation summary", "net asset value",
        "business valuation", "appraisal", "fair value"
    ],
    "quarterly_update_letter": [
        "quarter", "quarterly update", "quarterly report", "quarterly highlights",
        "recent highlights", "quarterly letter", "quarterly performance",
        "shareholder letter", "investor letter", "quarterly results",
        "quarterly earnings", "quarterly financial",
        "fourth quarter results", "full year results", "earnings release", "fiscal quarter"
    ],
}

def classify_text_rule(text: str) -> str:    
    lowered = text.lower()
    scores = {doc_type: 0 for doc_type in DOC_TYPES}
    for doc_type, keywords in DOC_TYPES.items():
        for kw in keywords:
            if kw in lowered:
                scores[doc_type] += 1
    best_type = max(scores, key=scores.get)
    return best_type if scores[best_type] > 0 else "unknown"


def classify_text(text: str) -> str:
    """
    AI-first classifier with rules fallback.    
    """
    use_ai = os.getenv("DOCINTEL_AI", "1") != "0"
    if use_ai:
        try:
            label, score, scores = classify_text_ai(text, threshold=0.55)
            
            if label != "unknown":
                return label
        except Exception as e:
            # Don't crash the pipeline if model fails; just fall back.
            print(f"[classifier] AI classify failed, falling back to rules: {e}")

    return classify_text_rule(text)
