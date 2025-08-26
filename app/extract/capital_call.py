import re
from dateutil import parser as dateparser
from decimal import Decimal, InvalidOperation


def extract_capital_call_fields(text: str):  

    data = {
        "fund_id": None,
        "call_date": None,
        "lp_id": None,
        "call_amount": None,
        "currency": None,
        "call_number": None,
    }

    lowered = text.lower()

    # --- Fund ID ---
    # Order matters: try to capture the full proper fund name first, then labeled lines
    fund_patterns = [
        # Labeled lines first (most reliable) - anchor to line start and require a colon
        r"(?im)^\s*fund id\s*:\s*([^\n\r]{2,100})",
        r"(?im)^\s*fund\s*:\s*([^\n\r]{2,100})",
        
        # Full fund name patterns - use word boundaries and avoid common header patterns
        # Look for fund names that start with proper nouns and end with Fund/Partnership
        r"\b([A-Z][A-Za-z0-9\-& ]*(?:\s+[A-Za-z0-9\-&]+)+\s+(?:Fund|Partnership)(?:\s+[IVX]+)?(?:\s*,?\s*LP)?)\b",
        r"\b([A-Z][A-Za-z0-9\-& ]+\s+Fund(?:\s+[IVX]+)?(?:\s*,?\s*LP)?)\b",
    ]
    
    for pattern in fund_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fund_id = match.group(1).strip()
            
            # Filter out matches that contain document header words
            header_words = ['capital call notice', 'capital call letter', 'drawdown notice', 'contribution notice']
            if not any(header_word in fund_id.lower() for header_word in header_words):
                data["fund_id"] = fund_id
                break

    # --- Call Date ---
    # try explicit labels first
    date_patterns = [
        # Pattern 1: "Call Date:" / "Due Date:" / "Payment Date:"
        r"(call date|due date|payment date)[:\s]+([A-Za-z]+\s+\d{1,2},\s*\d{4})",
        # Pattern 2: generic "Date: March 3, 2020"
        r"Date\s*[:\-]\s*([A-Za-z]+\s+\d{1,2},\s*\d{4})",
    ]

    for pattern in date_patterns:
        date_match = re.search(pattern, text, re.IGNORECASE)
        if date_match:
            try:
                # Some patterns capture 2 groups, some 1
                date_str = date_match.group(2) if date_match.lastindex >= 2 else date_match.group(1)
                data["call_date"] = dateparser.parse(date_str, fuzzy=True).date().isoformat()
                break
            except Exception:
                pass

    # Fallback: if still nothing, try *any* date-like string
    if not data["call_date"]:
        generic_date = re.search(r"([A-Za-z]+\s+\d{1,2},\s*\d{4})", text)
        if generic_date:
            try:
                data["call_date"] = dateparser.parse(generic_date.group(1), fuzzy=True).date().isoformat()
            except Exception:
                pass

    # --- LP ID ---
    lp_match = re.search(r"(lp id|limited partner id)[:\s]+([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    if lp_match:
        data["lp_id"] = lp_match.group(2).strip()

    # --- Call Amount ---

    # Prefer "Total Capital Call" / "Net Capital Call Due"
    amt_match = re.search(r"(Total Capital Call|Net Capital Call Due)\s*\$([\d,]+(?:\.\d{1,2})?)", text, re.IGNORECASE)
    if amt_match:
        data["currency"] = "$"
        data["call_amount"] = amt_match.group(2).replace(",", "")
    else:
        # fallback: choose closest $ amount to the word "call"
        amt_matches = re.findall(r"([\$€£])\s?([\d,]+(?:\.\d{1,2})?)", text)
        chosen_amt = None
        chosen_curr = None
        if amt_matches:
            call_idx = lowered.find("call")
            best_dist = float("inf")
            for curr, amt_str in amt_matches:
                amt_pos = text.find(curr + amt_str)
                dist = abs(amt_pos - call_idx) if call_idx != -1 else amt_pos
                if dist < best_dist:
                    best_dist = dist
                    chosen_curr = curr
                    try:
                        chosen_amt = str(Decimal(amt_str.replace(",", "")))
                    except InvalidOperation:
                        continue
        data["currency"] = chosen_curr
        data["call_amount"] = chosen_amt

    # --- Call Number ---

    # Look for patterns like "Call No. 3" or "Capital Call #2"
    callnum_match = re.search(r"(call (no\.|number|#)\s*)(\d+)", text, re.IGNORECASE)
    if callnum_match:
        data["call_number"] = callnum_match.group(3)

    return data
