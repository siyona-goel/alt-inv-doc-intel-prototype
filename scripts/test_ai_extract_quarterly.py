import pdfplumber
from app.extract.quarterly_update import extract_quarterly_update_fields
from app.extract.distribution import extract_distribution_fields
from app.extract.capital_call import extract_capital_call_fields
from app.extract.valuation_reports import extract_valuation_fields
from app.classify.classifier import classify_text

# PDF = "data/provided_dataset/quarterly update letter/third-point-q1-2025-investor-letter_tpil.pdf"
PDF = "data/Sample-Quarterly-1.pdf"

with pdfplumber.open(PDF) as pdf:
    text = "\n".join([p.extract_text() or "" for p in pdf.pages])

doc_type = classify_text(text)
print("CLASSIFIER:", doc_type)

# Call the appropriate extractor based on classification
if doc_type == "distribution_notice":
    res = extract_distribution_fields(text)
    print("\nEXTRACTING AS: Distribution Notice")
elif doc_type == "capital_call_letter":
    res = extract_capital_call_fields(text)
    print("\nEXTRACTING AS: Capital Call Letter")
elif doc_type == "valuation_reports":
    res = extract_valuation_fields(text)
    print("\nEXTRACTING AS: Valuation Report")
elif doc_type == "quarterly_update":
    res = extract_quarterly_update_fields(text)
    print("\nEXTRACTING AS: Quarterly Update")
else:
    print(f"\nUNKNOWN DOC TYPE: {doc_type}")
    res = {}

print("\nFINAL EXTRACTED:")
for k, v in res.items():
    if k.startswith("_"):
        continue
    print(f"{k}: {v}")
print("\nSOURCES:", res.get("_sources"))