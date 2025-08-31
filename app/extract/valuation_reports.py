import re
from dateutil import parser as dateparser
from decimal import Decimal, InvalidOperation

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


def extract_valuation_fields(text: str):

    data = {
        "valuation_date": None,
        "methodology": None,
        "inputs": {
            "discount_rate": None,
            "multiple": None,
        },
        "final_valuation": None,
        "currency": None,
    }

    # Normalize whitespace
    text_norm = re.sub(r"[\u00A0\t]", " ", text)

    # --- Valuation Date ---
    # Support formats like "December 31, 2024" (with optional comma) and other common variants
    date_patterns = [
        r"valuation\s*date[:\s-]*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})",
        r"valuation\s*date[:\s-]*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
        r"valuation\s*date[:\s-]*([^\n\r]+?\d{4})",
        r"as\s+(?:of|at)[:\s-]*([^\n\r]+?\d{4})",
        r"effective\s+date[:\s-]*([^\n\r]+?\d{4})",
        r"date\s+of\s+valuation[:\s-]*([^\n\r]+?\d{4})",
        r"valuation\s+as\s+(?:of|at)[:\s-]*([^\n\r]+?\d{4})",
        r"dated[:\s-]*([^\n\r]+?\d{4})",
        # Numeric formats fallback
        r"\b(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})\b",
    ]
    m = _first(text_norm, date_patterns)
    if m:
        candidate = m.group(1).strip().rstrip(".;,) ")
        for dayfirst in (False, True):
            try:
                data["valuation_date"] = dateparser.parse(candidate, fuzzy=True, dayfirst=dayfirst).date().isoformat()
                break
            except Exception:
                continue

    # --- Methodology ---
    def _canonicalize_methods(text_segment: str):
        findings = []
        positions = []
        # Income / DCF
        m_income = re.search(r"\b(discounted\s+cash\s+flow|DCF|income\s+approach)\b", text_segment, re.IGNORECASE)
        if m_income:
            findings.append("Discounted Cash Flow")
            positions.append(m_income.start())
        # Market
        m_market = re.search(r"\b(market\s+approach|comparable|guideline\s+public\s+company|precedent\s+transactions|multiples?)\b", text_segment, re.IGNORECASE)
        if m_market:
            findings.append("Market Approach")
            positions.append(m_market.start())
        # Cost
        m_cost = re.search(r"\b(cost\s+approach|asset[-\s]*based|net\s+asset\s+value|NAV)\b", text_segment, re.IGNORECASE)
        if m_cost:
            findings.append("Cost Approach")
            positions.append(m_cost.start())
        # Order by first occurrence to reflect document ordering
        if findings:
            ordered = [x for _, x in sorted(zip(positions, findings), key=lambda p: p[0])]
            # Deduplicate while keeping order
            seen = set()
            uniq = []
            for item in ordered:
                if item not in seen:
                    seen.add(item)
                    uniq.append(item)
            return "; ".join(uniq)
        return None

    # Prefer a labeled block near "Methodology" or similar
    header = re.search(r"^(?:.*\b(methodology|valuation\s+approach|basis\s+of\s+valuation)\b.*)$", text_norm, re.IGNORECASE | re.MULTILINE)
    methodology_text = None
    if header:
        start = header.start()
        # Look ahead a few lines from the header for details
        end = min(len(text_norm), start + 800)
        methodology_text = text_norm[start:end]
        canon = _canonicalize_methods(methodology_text)
        if canon:
            data["methodology"] = canon
    if data["methodology"] is None:
        # Fallback: scan entire document for canonical methods
        canon = _canonicalize_methods(text_norm)
        if canon:
            data["methodology"] = canon

    # --- Inputs ---
    discount_patterns = [
        r"(discount\s*rate|wacc|irr|required rate of return|capitalization rate|cap rate)[:\s-]*([\d]{1,2}(?:\.\d+)?)\s*%",
        r"(discount\s*rate|wacc|irr)\s*\(.*?\)[:\s-]*([\d]{1,2}(?:\.\d+)?)\s*%",
    ]
    m = _first(text_norm, discount_patterns)
    if m:
        data["inputs"]["discount_rate"] = m.group(2)

    multiple_patterns = [
        r"(ev/ebitda|ebitda multiple|revenue multiple|valuation multiple|multiple)[:\s-]*([\d]+(?:\.\d+)?)\s*x",
        r"multiple\s+of\s+([\d]+(?:\.\d+)?)\b",
    ]
    m = _first(text_norm, multiple_patterns)
    if m:
        val = m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)
        data["inputs"]["multiple"] = val

    # --- Final Valuation ---
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
            if not amt:
                start = max(0, m.start() - 50)
                end = min(len(text_norm), m.end() + 50)
                context = text_norm[start:end]
                cur, amt = _extract_currency_and_amount(context)
            if amt:
                data["final_valuation"] = amt
                data["currency"] = cur
                break

    if data["final_valuation"] is None:
        # Fallback: standalone header 'Valuation' and search in following context
        hdr = re.search(r"\bvaluation\b", text_norm, re.IGNORECASE)
        if hdr:
            start = hdr.start()
            end = min(len(text_norm), hdr.end() + 400)
            context = text_norm[start:end]
            cur, amt = _extract_currency_and_amount(context)
            if amt:
                data["final_valuation"] = amt
                data["currency"] = cur

    if data["final_valuation"] is None:
        m = re.search(r"\b(USD|EUR|GBP|INR|JPY|YEN|CAD|AUD|SGD|HKD|CHF|NZD|CNY|RMB)?\s*([$£€¥₹])?\s*([\d,.]+(?:\s*(?:million|billion|thousand|m|mm|bn|k))?)\b\s*(?:valuation|value)\b",
                      text_norm, re.IGNORECASE)
        if m:
            cur, amt = _extract_currency_and_amount(m.group(0))
            if amt:
                data["final_valuation"] = amt
                data["currency"] = cur

    # Global context-based fallback: find currency + amount near the word 'valuation'
    if data["final_valuation"] is None:
        currency_sign = r"[$£€¥₹]"
        currency_code = r"USD|EUR|GBP|INR|JPY|YEN|CAD|AUD|SGD|HKD|CHF|NZD|CNY|RMB|ZAR|SEK|NOK|DKK"
        amount_re = r"[\d,.]+(?:\s*(?:million|billion|thousand|m|mm|bn|k))?"
        any_money = re.finditer(rf"(?:\b({currency_code})\s*|({currency_sign})\s*)({amount_re})", text_norm, re.IGNORECASE)
        for m in any_money:
            start, end = m.start(), m.end()
            window_start = max(0, start - 200)
            window_end = min(len(text_norm), end + 200)
            window = text_norm[window_start:window_end]
            if re.search(r"\bvaluation\b", window, re.IGNORECASE):
                cur, amt = _extract_currency_and_amount(m.group(0))
                if amt:
                    data["final_valuation"] = amt
                    data["currency"] = cur
                    break

    return data
