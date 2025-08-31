"""
INITIAL IMPLEMENTATION: ONLY REGEX BASED

import re
from dateutil import parser as dateparser
from decimal import Decimal, InvalidOperation

def extract_distribution_fields(text: str):
    """
""" Extract key fields from a Distribution Notice document."""    
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
"""

"""data["currency"] = chosen_curr
    data["distribution_amount"] = chosen_amt"""

    # --- Type (ROC / CI) ---
    #if "return of capital" in lowered or re.search(r"\broc\b", lowered):
        #data["type"] = "ROC"
    #elif "capital income" in lowered or re.search(r"\bci\b", lowered):
        #data["type"] = "CI"
    # type None if neither pattern matches
    #return data
# ==========================================================================================================
""" AI INTEGRATED """

import re
from dateutil import parser as dateparser
from decimal import Decimal, InvalidOperation

from app.extract.ai_extractor import ai_extract_distribution_fields

def _parse_amount_simple(raw_amount: str):
    if not raw_amount:
        return None
    val = raw_amount.strip().lower().replace(",", "")
    # remove currency symbols/words
    val = re.sub(r"[$€£,]|usd|eur|gbp", "", val, flags=re.IGNORECASE)
    try:
        return str(Decimal(re.sub(r"[^\d\.]", "", val)))
    except InvalidOperation:
        # fallback: return raw
        return None

def _regex_fallback_fund_id(text):
    # Pattern 1: explicit "Fund ID: ..."
    m = re.search(r"(?im)^\s*fund id\s*[:\-]\s*(.+)$", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?im)^\s*fund\s*[:\-]\s*(.+)$", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"Board of Directors of ([A-Za-z0-9\-\& ]+)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # last-resort: first line that contains the word 'Fund' and looks like a name
    m = re.search(r"\b([A-Z][\w &\-.,]{2,80}\b\s+(Fund|Fund,|Fund:|Fund\s+[IVX]+))", text)
    if m:
        return m.group(1).strip()
    return None

def _regex_fallback_date(text):
    m = re.search(r"(distribution date|payable date|payment date)[:\s]+([A-Za-z]+\s+\d{1,2},\s+\d{4})", text, re.IGNORECASE)
    if m:
        try:
            return dateparser.parse(m.group(2), fuzzy=True).date().isoformat()
        except Exception:
            pass
    # fallback to first date-like string
    m = re.search(r"([A-Za-z]+\s+\d{1,2},\s+\d{4})", text)
    if m:
        try:
            return dateparser.parse(m.group(1), fuzzy=True).date().isoformat()
        except Exception:
            pass
    return None

def _regex_fallback_lp_id(text):
    m = re.search(r"(lp id|limited partner id)[:\s]+([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    if m:
        return m.group(2).strip()
    return None

def _regex_fallback_amount_and_currency(text):
    # try labeled totals first
    m = re.search(r"(Total Distribution|Total distribution|Distribution Amount|Total Amount|Net Distribution Due)\s*[:\-\s]*([$€£]?\s*[\d,]+(?:\.\d{1,2})?)", text, re.IGNORECASE)
    if m:
        cand = m.group(2)
        cur_match = re.search(r"([$€£])", cand)
        cur = cur_match.group(1) if cur_match else None
        amt = re.sub(r"[^\d\.]", "", cand)
        return cur, amt
    # fallback: find all currency amounts and choose closest to word "distribution"
    amt_matches = re.findall(r"([$€£])\s*([\d,]+(?:\.\d{1,2})?)", text)
    if not amt_matches:
        # try currency code with amount
        m = re.search(r"\b(USD|EUR|GBP)\s*([\d,]+(?:\.\d{1,2})?)", text, re.IGNORECASE)
        if m:
            return m.group(1).upper(), re.sub(r"[^\d\.]", "", m.group(2))
        return None, None
    # choose closest to word "distribution"
    lowered = text.lower()
    dist_idx = lowered.find("distribution")
    best = (None, None, float("inf"))
    for cur, amt in amt_matches:
        pos = text.find(cur + amt)
        dist = abs(pos - dist_idx) if dist_idx != -1 else pos
        if dist < best[2]:
            best = (cur, re.sub(r"[^\d\.]", "", amt), dist)
    return best[0], best[1]

def extract_distribution_fields(text: str):

    # run AI extractor first
    ai_results, ai_sources, ai_raw = ai_extract_distribution_fields(text)

    # prepare final structure
    data = {
        "fund_id": None,
        "distribution_date": None,
        "lp_id": None,
        "distribution_amount": None,
        "currency": None,
        "type": None,
    }
    sources = {}

    # copy AI results where confident
    for k in data.keys():
        v = ai_results.get(k) if ai_results else None
        s = ai_sources.get(k) if ai_sources else None
        if v:
            # some fields might need normalization
            if k == "distribution_amount":
                # if AI returned a number-like string, normalize
                data[k] = _parse_amount_simple(v) or v
            else:
                data[k] = v
            sources[k] = "ai"
        else:
            # mark ai_unconfident / error if AI tried
            if ai_results and (ai_sources.get(k) in ("ai_unconfident", "ai_error")):
                sources[k] = ai_sources.get(k)

    # --- Regex fallback for any fields that are missing or ai_unconfident ---
    if not data["fund_id"]:
        fallback = _regex_fallback_fund_id(text)
        if fallback:
            data["fund_id"] = fallback
            sources["fund_id"] = sources.get("fund_id") or "regex"

    if not data["distribution_date"]:
        fallback = _regex_fallback_date(text)
        if fallback:
            data["distribution_date"] = fallback
            sources["distribution_date"] = sources.get("distribution_date") or "regex"

    if not data["lp_id"]:
        fallback = _regex_fallback_lp_id(text)
        if fallback:
            data["lp_id"] = fallback
            sources["lp_id"] = sources.get("lp_id") or "regex"

    if not data["distribution_amount"] or not data["currency"]:
        cur, amt = _regex_fallback_amount_and_currency(text)
        if amt:
            data["distribution_amount"] = data["distribution_amount"] or amt
            data["currency"] = data["currency"] or cur
            sources["distribution_amount"] = sources.get("distribution_amount") or "regex"
            sources["currency"] = sources.get("currency") or "regex"

    # --- Type (ROC / CI) ---
    if not data["type"]:
        lowered = text.lower()
        if "return of capital" in lowered or re.search(r"\broc\b", lowered):
            data["type"] = "ROC"
            sources["type"] = sources.get("type") or "regex"
        elif "capital income" in lowered or re.search(r"\bci\b", lowered):
            data["type"] = "CI"
            sources["type"] = sources.get("type") or "regex"

    # Attach sources for observability
    data["_sources"] = sources
    # Optionally include raw AI outputs for debugging
    data["_ai_raw"] = ai_raw

    return data
