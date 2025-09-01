import pdfplumber
from app.extract.quarterly_update import extract_quarterly_update_fields
from app.classify.classifier import classify_text

PDF = "data/provided_dataset/quarterly update letter/third-point-q1-2025-investor-letter_tpil.pdf"
# PDF = "data/synthetic_quarterly_update.pdf"

with pdfplumber.open(PDF) as pdf:
    text = "\n".join([p.extract_text() or "" for p in pdf.pages])

print("CLASSIFIER:", classify_text(text))
res = extract_quarterly_update_fields(text)
print("\nFINAL EXTRACTED:")
for k, v in res.items():
    if k.startswith("_"):
        continue
    print(f"{k}: {v}")
print("\nSOURCES:", res.get("_sources"))