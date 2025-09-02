import re
from typing import Dict, List
from decimal import Decimal, InvalidOperation
from app.extract.ai_extractor import ai_extract_quarterly_fields

def _clean(text: str) -> str:
    if not text:
        return ""
    # Remove weird spaces, bullets, normalize line breaks
    text = re.sub(r"[\u2022\u2023\u25E6\u2043\u2219\*•]\s*", "- ", text)
    text = re.sub(r"[\t\u00A0]+", " ", text)
    text = text.replace("\r", "")
    return text.strip()


def _normalize_amount(raw: str) -> str:
    """Convert human-readable numbers (12.6 billion) into normalized form."""
    if not raw:
        return raw
    val = raw.strip().lower().replace(",", "")
    multiplier = Decimal(1)
    if "billion" in val or "bn" in val:
        multiplier = Decimal(1_000_000_000)
        val = re.sub(r"(billion|bn)", "", val)
    elif "million" in val or "mm" in val or val.endswith("m"):
        multiplier = Decimal(1_000_000)
        val = re.sub(r"(million|mm|m)", "", val)
    elif "thousand" in val or "k" in val:
        multiplier = Decimal(1_000)
        val = re.sub(r"(thousand|k)", "", val)

    try:
        num = Decimal(val.strip())
        return str((num * multiplier).quantize(Decimal("1")))
    except InvalidOperation:
        return raw  # fallback: return as-is


def _extract_kpis(text: str) -> List[Dict[str, str]]:
    """
    Extract KPIs from quarterly update text.
    Handles sentences like:
      - Revenues were $12.6 billion, up 5%
      - Gross margin decreased 50 bps to 43.6%
      - Diluted EPS was $0.99
    """
    kpis: List[Dict[str, str]] = []
    text = _clean(text)

    patterns = [
        # "Revenue was $12.6 billion"
        r"\b(Revenue|Revenues|Sales|Net income|Operating income|Gross margin|Operating margin|EPS|Earnings per share|Diluted earnings per share|Cash|Inventories)\b[^\n\r]{0,40}?\b(was|were|totaled|stood at|came in at)\b[^\n\r]{0,40}?([\$£€¥]?\s?[\d,.]+(?:\s*(?:billion|million|thousand|bn|mm|m|k|%|bps))?)",
        # "Gross margin decreased 50 bps to 43.6%"
        r"\b(Gross margin|Operating margin|EBITDA margin|Churn|Retention|Expenses|Costs)\b[^\n\r]{0,40}?\b(up|down|increased|decreased|expanded|declined|reduced|improved)\b[^\n\r]{0,40}?\s+to\s+([\d.,]+%|[\d.,]+\s*bps)",
    ]

    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            metric = m.group(1).strip()
            raw_value = m.group(3).strip()
            normalized_value = _normalize_amount(raw_value)

            kpis.append({
                "metric": metric,
                "value": normalized_value,
                "raw": raw_value
            })

    # Deduplicate
    seen = set()
    unique = []
    for item in kpis:
        key = (item["metric"].lower(), item["value"].lower() if item["value"] else item["raw"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


def _extract_highlights(text: str, max_items: int = 8) -> List[str]:
    """
    Extract key highlights: look for bullet lists or strong performance sentences.
    """
    text = _clean(text)
    highlights: List[str] = []

    # Bullet-style highlights
    for line in text.split("\n"):
        if re.match(r"^(\-|\d+\.|\([a-zA-Z0-9]\))\s+", line.strip()):
            clean_line = re.sub(r"^(\-|\d+\.|\([a-zA-Z0-9]\))\s+", "", line.strip())
            highlights.append(clean_line)

    # Narrative highlights
    if not highlights:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for s in sentences:
            if re.search(r"\b(revenue|sales|income|margin|eps|earnings|cash|launched|grew|up|increased|decreased|declined|expanded|record)\b",
                         s, re.IGNORECASE):
                highlights.append(s.strip())

    # Deduplicate + limit
    seen = set()
    result = []
    for h in highlights:
        if h and h.lower() not in seen:
            seen.add(h.lower())
            result.append(h)
            if len(result) >= max_items:
                break
    return result


def extract_quarterly_update_fields(text: str) -> Dict[str, object]:
    
    # Hybrid extractor for quarterly updates.
    # AI-first, falls back to regex if AI unconfident.
    
    text = text or ""

    # --- Run AI extractor first ---
    ai_res, ai_src, ai_raw = ai_extract_quarterly_fields(text)

    data = {
        "kpis": ai_res.get("kpis", []),
        "highlights": ai_res.get("highlights", []),
    }
    sources = {"kpis": {}, "highlights": None}

    # --- Regex fallback for KPIs ---
    if not data["kpis"]:
        data["kpis"] = _extract_kpis(text)
        sources["kpis"] = {"fallback": "regex"}
    else:
        sources["kpis"] = ai_src.get("kpis", {})

    # --- Regex fallback for Highlights ---
    if not data["highlights"]:
        data["highlights"] = _extract_highlights(text)
        sources["highlights"] = "regex"
    else:
        sources["highlights"] = ai_src.get("highlights", "ai")

    # Attach observability
    data["_sources"] = sources
    data["_ai_raw"] = ai_raw

    return data
