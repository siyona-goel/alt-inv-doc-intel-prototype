from __future__ import annotations
from transformers import pipeline
import threading
import re

# Simplified labels that match common document language
_LABELS = [
    ("capital_call_letter", "capital call notice"),
    ("distribution_notice", "distribution notice"), 
    ("valuation_reports", "valuation report"),
    ("quarterly_update_letter", "quarterly update"),
]

_HYPOTHESIS = "This document is a {}."
# _MODEL_NAME = "typeform/distilbert-base-uncased-mnli"
_MODEL_NAME = "facebook/bart-large-mnli"

_pipe = None
_lock = threading.Lock()

def _get_pipe():
    global _pipe
    if _pipe is None:
        with _lock:
            if _pipe is None:
                _pipe = pipeline(
                    task="zero-shot-classification",
                    model=_MODEL_NAME,
                    device=-1
                )
    return _pipe

def clean_text_for_ai(text: str) -> str:
    """Clean PDF text for better AI classification."""
    # Remove excessive whitespace and line breaks
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters that might confuse the model
    text = re.sub(r'[^\w\s.,;:!?()-]', ' ', text)
    return text.strip()

def classify_text_ai(text: str, threshold: float = 0.55):
    
    # Return (label_key, best_score, score_dict) using zero-shot classification.
    # If best_score < threshold, returns ('unknown', best_score, scores).
    
    if not text or not text.strip():
        return "unknown", 0.0, {}
    
    # Clean and truncate text for better results
    cleaned_text = clean_text_for_ai(text)
    
    # Take first 1500 chars (leaves room for model processing)
    if len(cleaned_text) > 1500:
        cleaned_text = cleaned_text[:1500]
    
    pipe = _get_pipe()

    candidate_texts = [desc for _, desc in _LABELS]
    
    try:
        result = pipe(
            cleaned_text,
            candidate_labels=candidate_texts,
            hypothesis_template=_HYPOTHESIS,
            multi_label=False,
        )
    except Exception as e:
        print(f"AI classification failed: {e}")
        return "unknown", 0.0, {}

    # Convert result back to keys
    scores = {}
    for label_text, score in zip(result["labels"], result["scores"]):
        idx = candidate_texts.index(label_text)
        key = _LABELS[idx][0]
        scores[key] = float(score)

    best_key = max(scores, key=scores.get)
    best_score = scores[best_key]
    
    if best_score < threshold:
        return "unknown", best_score, scores
    return best_key, best_score, scores