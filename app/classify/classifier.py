import re

# Four supported document types
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
        "quarterly update", "quarterly report", "quarterly highlights",
        "recent highlights", "quarterly letter", "quarterly performance",
        "shareholder letter", "investor letter", "quarterly results",
        "quarterly earnings", "quarterly financial"
        ]
}

def classify_text(text: str) -> str:
    
    lowered = text.lower()
    scores = {doc_type: 0 for doc_type in DOC_TYPES}

    for doc_type, keywords in DOC_TYPES.items():
        for kw in keywords:
            if kw in lowered:
                scores[doc_type] += 1

    # Pick doc_type with max score
    best_type = max(scores, key=scores.get)
    return best_type if scores[best_type] > 0 else "unknown"
