import pdfplumber
from app.extract.capital_call import extract_capital_call_fields
from app.classify.classifier import classify_text

PDF = "data/Sample-Capital-Call-Letter.pdf"

with pdfplumber.open(PDF) as pdf:
    text = "\n".join([p.extract_text() or "" for p in pdf.pages])

print("CLASSIFIER:", classify_text(text))
res = extract_capital_call_fields(text)
print("\nFINAL EXTRACTED:")
for k, v in res.items():
    if k.startswith("_"):
        continue
    print(f"{k}: {v}")
print("\nSOURCES:", res.get("_sources"))