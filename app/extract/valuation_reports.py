import re
from dateutil import parser as dateparser
from decimal import Decimal, InvalidOperation
from app.extract.ai_extractor import ai_extract_valuation_fields

def _first(text: str, patterns):
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match
    return None

def _parse_amount(raw_amount: str):
    # Normalize amounts like '1,234,567', '1.2 million', '2.5bn', '750k'.
    if not raw_amount:
        return None
    val = raw_amount.strip().rstrip(".;,) ").lower().replace(",", "")
    multiplier = Decimal(1)
    # Magnitude words
    if re.search(r"\b(million|mm|mio|m)\b", val):
        multiplier = Decimal(1_000_000)
        val = re.sub(r"\s*(million|mio|mm|m)\b", "", val)
    elif re.search(r"\b(billion|bn|b)\b", val):
        multiplier = Decimal(1_000_000_000)
        val = re.sub(r"\s*(billion|bn|b)\b", "", val)
    elif re.search(r"\b(thousand|k)\b", val):
        multiplier = Decimal(1_000)
        val = re.sub(r"\s*(thousand|k)\b", "", val)
    try:
        num = Decimal(val)
        return str((num * multiplier).quantize(Decimal("1"))) if multiplier != 1 else str(num)
    except InvalidOperation:
        return None


def _extract_currency_and_amount(text: str):

    currency = None
    amount = None

    currency_sign = r"[$£€¥₹]"
    currency_code = r"USD|EUR|GBP|INR|JPY|YEN|CAD|AUD|SGD|HKD|CHF|NZD|CNY|RMB|ZAR|SEK|NOK|DKK"

    patterns = [
        # Code then amount
        rf"\b({currency_code})\s*({currency_sign}?\s*[\d,.]+(?:\s*(?:million|billion|thousand|m|mm|bn|k))?)",
        # Sign then amount
        rf"({currency_sign})\s*([\d,.]+(?:\s*(?:million|billion|thousand|m|mm|bn|k))?)",
        # Amount then code in parens
        rf"([\d,.]+(?:\s*(?:million|billion|thousand|m|mm|bn|k))?)\s*\((?:in\s*)?({currency_code})\)",
        # Code then amount without space
        rf"\b({currency_code})([\d,.]+)\b",
    ]

    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            groups = [g for g in m.groups() if g]
            if len(groups) == 2:
                if re.fullmatch(currency_sign, groups[0]) or re.fullmatch(currency_code, groups[0], re.IGNORECASE):
                    currency = groups[0].upper()
                    amount = _parse_amount(groups[1])
                else:
                    amount = _parse_amount(groups[0])
                    currency = groups[1].upper()
            elif len(groups) == 1:
                amount = _parse_amount(groups[0])
            if amount:
                return currency, amount

    return None, None

def _regex_fallback_valuation_date(text):
    text_norm = re.sub(r"[\u00A0\t]", " ", text)
    date_patterns = [
        r"valuation\s*date[:\s-]*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})",
        r"valuation\s*date[:\s-]*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
        r"valuation\s*date[:\s-]*([^\n\r]+?\d{4})",
        r"as\s+(?:of|at)[:\s-]*([^\n\r]+?\d{4})",
        r"effective\s+date[:\s-]*([^\n\r]+?\d{4})",
        r"date\s+of\s+valuation[:\s-]*([^\n\r]+?\d{4})",
        r"valuation\s+as\s+(?:of|at)[:\s-]*([^\n\r]+?\d{4})",
        r"dated[:\s-]*([^\n\r]+?\d{4})",
        r"\b(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})\b",
    ]
    m = _first(text_norm, date_patterns)
    if m:
        candidate = m.group(1).strip().rstrip(".;,) ")
        for dayfirst in (False, True):
            try:
                return dateparser.parse(candidate, fuzzy=True, dayfirst=dayfirst).date().isoformat()
            except Exception:
                continue
    return None

# --- Methodology ---
def _regex_fallback_methodology(text):
    def _canonicalize_methods(segment: str):
        findings, positions = [], []
        m_income = re.search(r"\b(discounted\s+cash\s+flow|DCF|income\s+approach)\b", segment, re.IGNORECASE)
        if m_income:
            findings.append("Discounted Cash Flow"); positions.append(m_income.start())
        m_market = re.search(r"\b(market\s+approach|comparable|guideline\s+public\s+company|precedent\s+transactions|multiples?)\b", segment, re.IGNORECASE)
        if m_market:
            findings.append("Market Approach"); positions.append(m_market.start())
        m_cost = re.search(r"\b(cost\s+approach|asset[-\s]*based|net\s+asset\s+value|NAV)\b", segment, re.IGNORECASE)
        if m_cost:
            findings.append("Cost Approach"); positions.append(m_cost.start())
        if findings:
            ordered = [x for _, x in sorted(zip(positions, findings), key=lambda p: p[0])]
            seen, uniq = set(), []
            for item in ordered:
                if item not in seen:
                    seen.add(item); uniq.append(item)
            return "; ".join(uniq)
        return None

    header = re.search(r"^(?:.*\b(methodology|valuation\s+approach|basis\s+of\s+valuation)\b.*)$", text, re.IGNORECASE | re.MULTILINE)
    methodology_text = None
    if header:
        start, end = header.start(), min(len(text), header.start() + 800)
        methodology_text = text[start:end]
        canon = _canonicalize_methods(methodology_text)
        if canon:
            return canon
    return _canonicalize_methods(text)

# --- Inputs ---
def _regex_fallback_discount_rate(text):
    discount_patterns = [
        r"(discount\s*rate|wacc|irr|required rate of return|capitalization rate|cap rate)[:\s-]*([\d]{1,2}(?:\.\d+)?)\s*%",
        r"(discount\s*rate|wacc|irr)\s*\(.*?\)[:\s-]*([\d]{1,2}(?:\.\d+)?)\s*%",
    ]
    m = _first(text, discount_patterns)
    if m:
        return m.group(2)
    return None

def _regex_fallback_multiple(text):
    multiple_patterns = [
        r"(ev/ebitda|ebitda multiple|revenue multiple|valuation multiple|multiple)[:\s-]*([\d]+(?:\.\d+)?)\s*x",
        r"multiple\s+of\s+([\d]+(?:\.\d+)?)\b",
    ]
    m = _first(text, multiple_patterns)
    if m:
        return m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)
    return None

def _regex_fallback_final_valuation(text):
    text_norm = re.sub(r"[\u00A0\t]", " ", text)
    value_clauses = [
        r"conclusion of value[:\s-]*([^\n\r]+)",
        r"fair value[:\s-]*([^\n\r]+)",
        r"final valuation[:\s-]*([^\n\r]+)",
        r"(equity value|enterprise value|market value|valuation)[:\s-]*([^\n\r]+)",
    ]
    for pat in value_clauses:
        m = re.search(pat, text_norm, re.IGNORECASE)
        if m:
            segment = m.group(m.lastindex or 1)
            cur, amt = _extract_currency_and_amount(segment)
            if amt:
                return cur, amt
    return None, None

def extract_valuation_fields(text: str):
    ai_results, ai_sources, ai_raw = ai_extract_valuation_fields(text)

    data = {
        "valuation_date": ai_results.get("valuation_date"),
        "methodology": ai_results.get("methodology"),
        "inputs": {
            "discount_rate": ai_results.get("discount_rate"),
            "multiple": ai_results.get("multiple"),
        },
        "final_valuation": ai_results.get("final_valuation"),
        "currency": ai_results.get("currency"),
    }
    sources = {k: v for k, v in ai_sources.items() if v}

    # Regex fallback for missing
    if not data["valuation_date"]:
        v = _regex_fallback_valuation_date(text)
        if v: data["valuation_date"] = v; sources["valuation_date"] = "regex"

    if not data["methodology"]:
        v = _regex_fallback_methodology(text)
        if v: data["methodology"] = v; sources["methodology"] = "regex"

    if not data["inputs"]["discount_rate"]:
        v = _regex_fallback_discount_rate(text)
        if v: data["inputs"]["discount_rate"] = v; sources["discount_rate"] = "regex"

    if not data["inputs"]["multiple"]:
        v = _regex_fallback_multiple(text)
        if v: data["inputs"]["multiple"] = v; sources["multiple"] = "regex"

    if not data["final_valuation"]:
        cur, amt = _regex_fallback_final_valuation(text)
        if amt: data["final_valuation"] = amt; data["currency"] = cur; sources["final_valuation"] = "regex"

    data["_sources"] = sources
    data["_ai_raw"] = ai_raw
    return data
