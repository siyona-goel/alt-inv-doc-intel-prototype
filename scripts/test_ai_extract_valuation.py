import pdfplumber
from app.extract.valuation_reports import extract_valuation_fields
from app.classify.classifier import classify_text

PDF = "data/Sample-Valuation-3.pdf"

with pdfplumber.open(PDF) as pdf:
    text = "\n".join([p.extract_text() or "" for p in pdf.pages])

print("CLASSIFIER:", classify_text(text))
res = extract_valuation_fields(text)
print("\nFINAL EXTRACTED:")
for k, v in res.items():
    if k.startswith("_"):
        continue
    print(f"{k}: {v}")
print("\nSOURCES:", res.get("_sources"))