import threading
import re
import os
from transformers import pipeline
from decimal import Decimal, InvalidOperation

_MODEL_QA = "deepset/roberta-large-squad2"  # SQuAD-style QA model
_pipe_qa = None
_lock = threading.Lock()

def _get_qa_pipe():
    global _pipe_qa
    if _pipe_qa is None:
        with _lock:
            if _pipe_qa is None:
                _pipe_qa = pipeline("question-answering", model=_MODEL_QA, device=-1)
    return _pipe_qa

def _clean_text(text: str, max_chars: int = 4000) -> str:
    if not text:
        return ""
    # Basic normalization: collapse whitespace and remove odd control chars
    txt = re.sub(r'[\u00A0\t\r]+', ' ', text)
    txt = re.sub(r'\s+', ' ', txt)
    txt = re.sub(r'[^\x00-\x7F]+', ' ', txt)  # remove non-ascii glyphs that can confuse tokens
    txt = txt.strip()
    return txt[:max_chars]

def _parse_amount(raw_amount: str):
    """Normalize amounts like '1,234,567', '1.2 million', '2.5bn', '750k' -> digits string."""
    if not raw_amount:
        return None
    val = raw_amount.strip().lower().replace(",", "")
    multiplier = Decimal(1)
    if re.search(r"\b(million|mm|mio|m)\b", val):
        multiplier = Decimal(1_000_000)
        val = re.sub(r"\s*(million|mio|mm|m)\b", "", val)
    elif re.search(r"\b(billion|bn|b)\b", val):
        multiplier = Decimal(1_000_000_000)
        val = re.sub(r"\s*(billion|bn|b)\b", "", val)
    elif re.search(r"\b(thousand|k)\b", val):
        multiplier = Decimal(1_000)
        val = re.sub(r"\s*(thousand|k)\b", "", val)
    # strip percent etc.
    val = re.sub(r"[^\d\.\-]", "", val)
    try:
        num = Decimal(val)
        if multiplier != 1:
            return str((num * multiplier).quantize(Decimal("1")))
        return str(num)
    except InvalidOperation:
        return None

def _extract_currency_and_amount_from_text(s: str):
    """Return (currency_symbol_or_code, normalized_amount) or (None, None)."""
    if not s:
        return None, None
    # look for sign + amount
    m = re.search(r"([$€£¥])\s*([\d,]+(?:\.\d+)?)", s)
    if m:
        cur = m.group(1)
        amt = _parse_amount(m.group(2))
        return cur, amt
    # look for code then number: "USD 1,234,567"
    m = re.search(r"\b(USD|EUR|GBP|JPY|AUD|CAD|SGD|HKD|CHF|CNY)\b\s*([\d,]+(?:\.\d+)?)", s, re.IGNORECASE)
    if m:
        cur = m.group(1).upper()
        amt = _parse_amount(m.group(2))
        return cur, amt
    # textual magnitude e.g. "1.2 million"
    m = re.search(r"([\d,.]+\s*(?:million|billion|thousand|bn|mm|k))", s, re.IGNORECASE)
    if m:
        amt = _parse_amount(m.group(1))
        return None, amt
    # bare numeric
    m = re.search(r"([\d,]{3,}(?:\.\d+)?)", s)
    if m:
        return None, _parse_amount(m.group(1))
    return None, None

def ai_extract_distribution_fields(text: str, min_score: float = 0.20, context_chars: int = 4000):
    """
    AI-first extraction for distribution fields using QA pipeline.
    Returns: (results_dict, sources_dict, raw_ai_responses_dict)
    - results_dict: {field: value_or_None}
    - sources_dict: {field: "ai" | "regex" | "ai_unconfident" | "ai_error"}
    - raw_ai_responses_dict: raw answer + score for debugging
    """
    # Optionally allow turning AI off
    if os.getenv("DOCINTEL_AI", "1") == "0":
        return {}, {}, {}

    ctx = _clean_text(text, max_chars=context_chars)
    qa = _get_qa_pipe()

    questions = {
        "fund_id": "What is the name or ID of the fund?",
        "distribution_date": "What is the distribution date?",
        "lp_id": "What is the LP ID or limited partner ID?",
        "distribution_amount": "What is the distribution amount?",
        "type": "Is this distribution described as Return of Capital (ROC) or Capital Income (CI)?",
    }

    results = {k: None for k in questions}
    sources = {k: None for k in questions}
    raw = {}

    for key, q in questions.items():
        try:
            out = qa(question=q, context=ctx)
            ans = out.get("answer", "").strip()
            score = float(out.get("score", 0.0))
            raw[key] = {"answer": ans, "score": score}
            if not ans or score < min_score:
                # AI tried but is unconfident
                results[key] = None
                sources[key] = "ai_unconfident"
                continue

            # postprocess per-field
            if key == "distribution_amount":
                # try to parse currency/amount from the answer
                cur, amt = _extract_currency_and_amount_from_text(ans)
                # if QA returned e.g. "USD 517,000" we pick both
                results["distribution_amount"] = amt
                # set currency if we found it
                if cur:
                    results["currency"] = cur
                sources[key] = "ai"
                if results["distribution_amount"]:
                    # ensure currency exists even if not in answer
                    sources["currency"] = sources.get("currency", "ai") if results.get("currency')") else "ai"
            elif key == "type":
                a = ans.lower()
                if "return of capital" in a or "roc" in a:
                    results["type"] = "ROC"
                elif "capital income" in a or "ci" in a:
                    results["type"] = "CI"
                else:
                    results["type"] = None
                sources["type"] = "ai"
            else:
                results[key] = ans if ans else None
                sources[key] = "ai"
        except Exception as e:
            raw[key] = {"error": str(e)}
            results[key] = None
            sources[key] = "ai_error"

    # If AI provided currency only via distribution_amount parsing, ensure result present
    if results.get("currency") is None:
        # try to find currency in context near words "distribution"
        m = re.search(r"(distribution[^.]{0,80}([$€£]|USD|EUR|GBP))", text, re.IGNORECASE)
        if m:
            cands = re.findall(r"([$€£]|USD|EUR|GBP)", m.group(0), re.IGNORECASE)
            if cands:
                results["currency"] = cands[0].upper()
                sources["currency"] = "ai_context"

    return results, sources, raw

def ai_extract_capital_call_fields(
    text: str,
    min_score: float = 0.20,
    context_chars: int = 4000
):
    """
    AI-first extraction for Capital Call letters using QA pipeline.
    Returns: (results_dict, sources_dict, raw_ai_responses_dict)
    - results_dict: {field: value_or_None}
    - sources_dict: {field: "ai" | "regex" | "ai_unconfident" | "ai_error"}
    - raw_ai_responses_dict: raw answer + score for debugging
    """
    if os.getenv("DOCINTEL_AI", "1") == "0":
        return {}, {}, {}

    ctx = _clean_text(text, max_chars=context_chars)
    qa = _get_qa_pipe()

    questions = {
        "fund_id": "What is the Fund name or Fund ID in this capital call letter?",
        "call_date": "What is the call date, due date, or payment date?",
        "lp_id": "What is the Limited Partner ID?",
        "call_amount": "What is the total capital call amount requested?",
        "currency": "What is the currency of the capital call?",
        "call_number": "What is the call number or sequence (e.g., Call No. 3)?",
    }

    results = {k: None for k in questions}
    sources = {k: None for k in questions}
    raw = {}

    for key, q in questions.items():
        try:
            out = qa(question=q, context=ctx)
            ans = out.get("answer", "").strip()
            score = float(out.get("score", 0.0))
            raw[key] = {"answer": ans, "score": score}

            if not ans or score < min_score:
                results[key] = None
                sources[key] = "ai_unconfident"
                continue

            # postprocess
            if key == "call_amount":
                cur, amt = _extract_currency_and_amount_from_text(ans)
                results["call_amount"] = amt
                if cur:
                    results["currency"] = cur
                sources[key] = "ai"
                if results["call_amount"]:
                    sources["currency"] = sources.get("currency", "ai")
            elif key == "currency":
                # normalize to symbol or code
                cur, _ = _extract_currency_and_amount_from_text(ans)
                results["currency"] = cur or ans
                sources[key] = "ai"
            else:
                results[key] = ans
                sources[key] = "ai"

        except Exception as e:
            raw[key] = {"error": str(e)}
            results[key] = None
            sources[key] = "ai_error"

    # If AI missed currency, attempt context lookup near "capital call"
    if results.get("currency") is None:
        m = re.search(r"(capital call[^.]{0,80}([$€£]|USD|EUR|GBP))", text, re.IGNORECASE)
        if m:
            cands = re.findall(r"([$€£]|USD|EUR|GBP)", m.group(0), re.IGNORECASE)
            if cands:
                results["currency"] = cands[0].upper()
                sources["currency"] = "ai_context"

    return results, sources, raw

def ai_extract_valuation_fields(
    text: str,
    min_score: float = 0.20,
    context_chars: int = 4000
):
    """
    AI-first extraction for Valuation Reports using QA pipeline.
    Returns: (results_dict, sources_dict, raw_ai_responses_dict)
    """
    if os.getenv("DOCINTEL_AI", "1") == "0":
        return {}, {}, {}

    ctx = _clean_text(text, max_chars=context_chars)
    qa = _get_qa_pipe()

    questions = {
        "valuation_date": "What is the valuation date of the report?",
        "methodology": "What methodology or valuation approach was used (e.g., DCF, Market Approach, Cost Approach)?",
        "discount_rate": "What discount rate was applied in the valuation?",
        "multiple": "What multiples (e.g., EBITDA multiple, revenue multiple) were used?",
        "final_valuation": "What is the final or concluded valuation amount?",
        "currency": "What is the currency of the final valuation?",
    }

    results = {k: None for k in questions}
    sources = {k: None for k in questions}
    raw = {}

    for key, q in questions.items():
        try:
            out = qa(question=q, context=ctx)
            ans = out.get("answer", "").strip()
            score = float(out.get("score", 0.0))
            raw[key] = {"answer": ans, "score": score}

            if not ans or score < min_score:
                results[key] = None
                sources[key] = "ai_unconfident"
                continue

            if key == "final_valuation":
                cur, amt = _extract_currency_and_amount_from_text(ans)
                results["final_valuation"] = amt or ans
                if cur:
                    results["currency"] = cur
                sources[key] = "ai"
                if results["final_valuation"]:
                    sources["currency"] = sources.get("currency", "ai")
            elif key in ("discount_rate", "multiple"):
                # Strip % or x
                val = re.sub(r"[^\d\.]", "", ans)
                results[key] = val or ans
                sources[key] = "ai"
            elif key == "currency":
                cur, _ = _extract_currency_and_amount_from_text(ans)
                results["currency"] = cur or ans
                sources[key] = "ai"
            else:
                results[key] = ans
                sources[key] = "ai"

        except Exception as e:
            raw[key] = {"error": str(e)}
            results[key] = None
            sources[key] = "ai_error"

    return results, sources, raw

def ai_extract_quarterly_fields(
    text: str,
    min_score: float = 0.15,
    context_chars: int = 4000,
    metrics: list | None = None,
    max_kpis: int = 12,
    max_highlights: int = 8
):
    """
    AI-first extraction for Quarterly Update fields using QA.
    Returns:
      results: {"kpis": [ {metric, value, currency, pct_change, raw}, ... ], "highlights": [str,...]}
      sources: {"kpis": {metric: "ai"|"ai_unconfident"|"ai_error"}, "highlights": "ai"|"ai_unconfident"|"ai_error"}
      raw: raw per-question responses for debugging
    """

    # If AI disabled via ENV, quick exit
    if os.getenv("DOCINTEL_AI", "1") == "0":
        return {"kpis": [], "highlights": []}, {"kpis": {}, "highlights": "ai_off"}, {}

    ctx = _clean_text(text, max_chars=context_chars)
    qa = _get_qa_pipe()

    if metrics is None:
        metrics = [
            "Revenue", "ARR", "Net income", "Operating income", "Gross margin",
            "EBITDA", "EBITDA margin", "EPS", "Cash", "Users", "Churn", "Bookings",
            "Retention", "ARPU", "CAC", "Subscriptions"
        ]

    results = {"kpis": [], "highlights": []}
    sources = {"kpis": {}, "highlights": None}
    raw = {}

    # Helper to parse percent/bps in a short string
    def _parse_pct(s: str):
        if not s:
            return None
        m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%|\b(\d+(?:\.\d+)?)\s*bps\b", s, re.IGNORECASE)
        if not m:
            return None
        if m.group(1):
            return m.group(1).strip() + "%"
        if m.group(2):
            return m.group(2).strip() + " bps"
        return None

    # Ask targeted KPI questions
    for metric in metrics:
        q = f"What is the {metric} reported in this document? Provide the value and percent change if available."
        try:
            out = qa(question=q, context=ctx)
            ans = (out.get("answer") or "").strip()
            score = float(out.get("score", 0.0))
            raw[metric] = {"answer": ans, "score": score}
            if not ans or score < min_score:
                sources["kpis"][metric] = "ai_unconfident"
                continue

            # parse currency/amount and percent
            cur, amt = _extract_currency_and_amount_from_text(ans)
            pct = _parse_pct(ans)

            # build KPI record if anything found (amount or pct)
            if amt or pct:
                rec = {
                    "metric": metric,
                    "value": amt,
                    "currency": cur,
                    "pct_change": pct,
                    "raw": ans,
                }
                results["kpis"].append(rec)
                sources["kpis"][metric] = "ai"
            else:
                # Sometimes the answer might be textual ("unchanged", "no material change")
                # Keep the raw answer so downstream code can inspect
                rec = {
                    "metric": metric,
                    "value": None,
                    "currency": None,
                    "pct_change": None,
                    "raw": ans,
                }
                results["kpis"].append(rec)
                sources["kpis"][metric] = "ai"

            # stop early if we've gathered enough KPIs
            if len(results["kpis"]) >= max_kpis:
                break

        except Exception as e:
            raw[metric] = {"error": str(e)}
            sources["kpis"][metric] = "ai_error"
            continue

    # Extract narrative highlights: ask QA to return a compact list separated by a sentinel
    qh = f"List up to {max_highlights} one-sentence highlights about performance, growth, or strategic events from this document. Separate each highlight with '||'."
    try:
        out_h = qa(question=qh, context=ctx)
        ans_h = (out_h.get("answer") or "").strip()
        score_h = float(out_h.get("score", 0.0))
        raw["highlights"] = {"answer": ans_h, "score": score_h}
        if ans_h and score_h >= min_score:
            # Prefer explicit separator if model used it
            if "||" in ans_h:
                parts = [p.strip() for p in ans_h.split("||") if p.strip()]
            else:
                # fallback: split into sentences
                parts = [p.strip().rstrip(".;") for p in re.split(r"(?<=[.!?])\s+", ans_h) if len(p.strip()) > 10]
            # filter short or junk items
            parts = [p for p in parts if len(p) > 10]
            results["highlights"] = parts[:max_highlights]
            sources["highlights"] = "ai"
        else:
            sources["highlights"] = "ai_unconfident"
    except Exception as e:
        raw["highlights"] = {"error": str(e)}
        sources["highlights"] = "ai_error"

    return results, sources, raw
