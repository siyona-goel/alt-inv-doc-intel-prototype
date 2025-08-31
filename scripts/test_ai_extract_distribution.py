import pdfplumber
from app.extract.distribution import extract_distribution_fields
from app.classify.classifier import classify_text

PDF = "data/synthetic_dist_notice_1.pdf"

with pdfplumber.open(PDF) as pdf:
    text = "\n".join([p.extract_text() or "" for p in pdf.pages])

print("CLASSIFIER:", classify_text(text))
res = extract_distribution_fields(text)
print("\nFINAL EXTRACTED:")
for k, v in res.items():
    if k.startswith("_"):
        continue
    print(f"{k}: {v}")
print("\nSOURCES:", res.get("_sources"))
# print("\nAI raw responses (debug):", res.get("_ai_raw"))
