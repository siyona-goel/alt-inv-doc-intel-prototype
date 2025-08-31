# scripts/test_ai_classifier.py
import pdfplumber
from app.classify.ai_classifier import classify_text_ai
from app.classify.classifier import classify_text_rule

PDF = "data/Sample-Valuation-3.pdf"

with pdfplumber.open(PDF) as pdf:
    text = "\n".join([p.extract_text() or "" for p in pdf.pages])

label, score, scores = classify_text_ai(text)
print("AI predicted:", label, "score:", round(score, 3))
print("All scores:", {k: round(v, 3) for k, v in scores.items()})

rule_label = classify_text_rule(text)
print("Rules predicted:", rule_label)


"""import pdfplumber
from app.classify.ai_classifier import classify_text_ai
from app.classify.classifier import classify_text_rule

PDF = "data/Sample-Valuation-3.pdf"

with pdfplumber.open(PDF) as pdf:
    text = "\n".join([p.extract_text() or "" for p in pdf.pages])

print("=== DEBUGGING AI CLASSIFIER ===")
print(f"Total text length: {len(text)} characters")
print("First 300 chars:")
print(repr(text[:300]))
print()

# Test with very low threshold
label, score, scores = classify_text_ai(text, threshold=0.1)
print("AI predicted (low threshold):", label, "score:", round(score, 3))
print("All scores:", {k: round(v, 3) for k, v in scores.items()})
print()

# Test with simple, obvious text
test_cases = [
    "This is a capital call notice requesting funding",
    "Distribution payment notification for quarterly dividends", 
    "Valuation report showing net asset values",
    "Quarterly update letter with performance highlights"
]

print("=== TESTING WITH SIMPLE TEXT ===")
for test_text in test_cases:
    label, score, scores = classify_text_ai(test_text, threshold=0.3)
    print(f"Text: '{test_text}'")
    print(f"AI predicted: {label} (score: {round(score, 3)})")
    print()

print("=== RULES COMPARISON ===")
rule_label = classify_text_rule(text)
print("Rules predicted:", rule_label)
"""
