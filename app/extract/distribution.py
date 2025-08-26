import re
from dateutil import parser as dateparser
from decimal import Decimal, InvalidOperation

def extract_distribution_fields(text: str):
    """
    Extract key fields from a Distribution Notice document.    
    """

    data = {
        "fund_id": None,
        "distribution_date": None,
        "lp_id": None,
        "distribution_amount": None,
        "currency": None,
        "type": None,
    }

    lowered = text.lower()

    # --- Fund ID ---
    # Pattern 1: "Fund ID: ABC123"
    match = re.search(r"fund id[:\s]+([A-Za-z0-9\-\&() ]{2,50})", text, re.IGNORECASE)
    if match:
        data["fund_id"] = match.group(1).strip()
    else:
        # Pattern 2: Simple format "Fund: XYZ Fund Name"
        match = re.search(r"fund[:\s]+([A-Za-z0-9\-\&() ]{2,50})", text, re.IGNORECASE)
        if match:
            data["fund_id"] = match.group(1).strip()
        else:
            # Pattern 3: Legal document format "Board of Directors of XYZ Fund (the Fund)"
            match = re.search(r"Board of Directors of ([A-Za-z0-9\-\& ]+)", text, re.IGNORECASE)
            if match:
                data["fund_id"] = match.group(1).strip()

    # --- Distribution Date ---
    date_match = re.search(
        # check for dates next to keywords related to 'distribution'
        r"(distribution date|payable date|payment date)[:\s]+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        text,
        re.IGNORECASE,
    )
    if date_match:
        try:
            # Normalize to ISO format (YYYY-MM-DD)
            data["distribution_date"] = (
                dateparser.parse(date_match.group(2), fuzzy=True).date().isoformat()
            )
        except Exception:
            pass
    else:
        # Fallback: just grab the first date-like string
        # assumption used: docs mention distribution date early
        date_match = re.search(r"([A-Za-z]+\s+\d{1,2},\s+\d{4})", text)
        if date_match:
            try:
                data["distribution_date"] = (
                    dateparser.parse(date_match.group(1), fuzzy=True).date().isoformat()
                )
            except Exception:
                pass

    # --- LP ID ---
    # Look for LP ID or Limited Partner ID followed by alphanumeric identifier
    lp_match = re.search(r"(lp id|limited partner id)[:\s]+([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    if lp_match:
        data["lp_id"] = lp_match.group(2).strip()

    # --- Distribution Amount ---
    # have to figure out which amt in the doc is actually the distribution amount
    # Grab *all* currency amounts
    amt_matches = re.findall(r"([\$€£])\s?([\d,]+(?:\.\d{1,2})?)", text)
    chosen_amt = None
    chosen_curr = None
    if amt_matches:
        # Heuristic: pick the amount that appears closest to the word "distribution"
        dist_idx = lowered.find("distribution")
        best_dist = float("inf")
        for match in amt_matches:
            curr, amt_str = match

            # find where amount appears
            amt_pos = text.find(match[0] + amt_str)
            # calculate distance from "distribution"
            dist = abs(amt_pos - dist_idx) if dist_idx != -1 else amt_pos
            # keep track of closest amount to "distribution"
            if dist < best_dist:
                best_dist = dist
                chosen_curr = curr
                try:
                    chosen_amt = str(Decimal(amt_str.replace(",", "")))
                except InvalidOperation:
                    continue

    data["currency"] = chosen_curr
    data["distribution_amount"] = chosen_amt

    # --- Type (ROC / CI) ---
    if "return of capital" in lowered or re.search(r"\broc\b", lowered):
        data["type"] = "ROC"
    elif "capital income" in lowered or re.search(r"\bci\b", lowered):
        data["type"] = "CI"
    # type None if neither pattern matches
    return data
