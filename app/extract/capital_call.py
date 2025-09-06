import re
from dateutil import parser as dateparser
from decimal import Decimal, InvalidOperation

from app.extract.ai_extractor import ai_extract_capital_call_fields


def _parse_amount_simple(raw_amount: str):
    if not raw_amount:
        return None
    val = raw_amount.strip().lower().replace(",", "")
    val = re.sub(r"[$€£,]|usd|eur|gbp", "", val, flags=re.IGNORECASE)
    try:
        return str(Decimal(re.sub(r"[^\d\.]", "", val)))
    except InvalidOperation:
        return None


# -------------------- Regex fallback helpers --------------------

def _regex_fallback_fund_id(text):
    fund_patterns = [
        # Labeled lines first (most reliable)
        r"(?im)^\s*fund id\s*[:\-]\s*([^\n\r]{2,100})",
        r"(?im)^\s*fund\s*[:\-]\s*([^\n\r]{2,100})",

        # Full fund name patterns
        r"\b([A-Z][A-Za-z0-9\-& ]*(?:\s+[A-Za-z0-9\-&]+)+\s+(?:Fund|Partnership)(?:\s+[IVX]+)?(?:,?\s*LP)?)\b",
        r"\b([A-Z][A-Za-z0-9\-& ]+\s+Fund(?:\s+[IVX]+)?(?:,?\s*LP)?)\b",
    ]

    for pattern in fund_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fund_id = match.group(1).strip()

            # filter out matches that are just headers, not actual fund names
            header_words = [
                "capital call notice",
                "capital call letter",
                "drawdown notice",
                "contribution notice",
            ]
            if not any(h in fund_id.lower() for h in header_words):
                return fund_id

    return None

def _regex_fallback_date(text):
    date_patterns = [
        # Explicit labels
        r"(call date|due date|payment date)[:\s]+([A-Za-z]+\s+\d{1,2},\s*\d{4})",
        # Generic "Date: March 3, 2020"
        r"Date\s*[:\-]\s*([A-Za-z]+\s+\d{1,2},\s*\d{4})",
    ]

    for pattern in date_patterns:
        date_match = re.search(pattern, text, re.IGNORECASE)
        if date_match:
            try:
                # choose correct group depending on pattern
                date_str = date_match.group(2) if date_match.lastindex >= 2 else date_match.group(1)
                return dateparser.parse(date_str, fuzzy=True).date().isoformat()
            except Exception:
                continue

    # fallback: *any* date-like string
    generic_date = re.search(r"([A-Za-z]+\s+\d{1,2},\s*\d{4})", text)
    if generic_date:
        try:
            return dateparser.parse(generic_date.group(1), fuzzy=True).date().isoformat()
        except Exception:
            pass

    return None

def _regex_fallback_lp_id(text):
    m = re.search(r"(lp id|limited partner id)[:\s]+([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    if m:
        return m.group(2).strip()
    return None


def _regex_fallback_amount_and_currency(text):
    # look for "Total Capital Call" style
    m = re.search(r"(Total Capital Call|Net Capital Call Due)\s*[:\-]?\s*([$€£]?\s*[\d,]+(?:\.\d{1,2})?)",
                  text, re.IGNORECASE)
    if m:
        cand = m.group(2)
        cur_match = re.search(r"([$€£])", cand)
        cur = cur_match.group(1) if cur_match else None
        amt = re.sub(r"[^\d\.]", "", cand)
        return cur, amt

    # fallback: nearest amount to word "call"
    amt_matches = re.findall(r"([$€£])\s*([\d,]+(?:\.\d{1,2})?)", text)
    if not amt_matches:
        m = re.search(r"\b(USD|EUR|GBP)\s*([\d,]+(?:\.\d{1,2})?)", text, re.IGNORECASE)
        if m:
            return m.group(1).upper(), re.sub(r"[^\d\.]", "", m.group(2))
        return None, None

    lowered = text.lower()
    call_idx = lowered.find("call")
    best = (None, None, float("inf"))
    for cur, amt in amt_matches:
        pos = text.find(cur + amt)
        dist = abs(pos - call_idx) if call_idx != -1 else pos
        if dist < best[2]:
            best = (cur, re.sub(r"[^\d\.]", "", amt), dist)
    return best[0], best[1]


def _regex_fallback_call_number(text):
    m = re.search(r"(call (no\.|number|#)\s*)(\d+)", text, re.IGNORECASE)
    if m:
        return m.group(3)
    return None

def extract_capital_call_fields(text: str):

    # Run AI extractor first
    ai_results, ai_sources, ai_raw = ai_extract_capital_call_fields(text)

    data = {
        "fund_id": None,
        "call_date": None,
        "lp_id": None,
        "call_amount": None,
        "currency": None,
        "call_number": None,
    }
    sources = {}

    # Copy confident AI results
    for k in data.keys():
        v = ai_results.get(k) if ai_results else None
        s = ai_sources.get(k) if ai_sources else None
        if v:
            if k == "call_amount":
                data[k] = _parse_amount_simple(v) or v
            else:
                data[k] = v
            sources[k] = "ai"
        else:
            if ai_sources.get(k) in ("ai_unconfident", "ai_error"):
                sources[k] = ai_sources.get(k)

    # Regex fallback for missing/unconfident
    if not data["fund_id"]:
        fb = _regex_fallback_fund_id(text)
        if fb:
            data["fund_id"] = fb
            sources["fund_id"] = sources.get("fund_id") or "regex"

    if not data["call_date"]:
        fb = _regex_fallback_date(text)
        if fb:
            data["call_date"] = fb
            sources["call_date"] = sources.get("call_date") or "regex"

    if not data["lp_id"]:
        fb = _regex_fallback_lp_id(text)
        if fb:
            data["lp_id"] = fb
            sources["lp_id"] = sources.get("lp_id") or "regex"

    if not data["call_amount"] or not data["currency"]:
        cur, amt = _regex_fallback_amount_and_currency(text)
        if amt:
            data["call_amount"] = data["call_amount"] or amt
            data["currency"] = data["currency"] or cur
            sources["call_amount"] = sources.get("call_amount") or "regex"
            sources["currency"] = sources.get("currency") or "regex"

    if not data["call_number"]:
        fb = _regex_fallback_call_number(text)
        if fb:
            data["call_number"] = fb
            sources["call_number"] = sources.get("call_number") or "regex"

    # Attach metadata
    data["_sources"] = sources
    data["_ai_raw"] = ai_raw

    return data
