import re


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text.lower())


def _syllables(word: str) -> int:
    return max(1, len(re.findall(r"[aeiouy]+", word.lower())))


def seo_stats(text: str, keywords: list[str]) -> dict:
    """Local SEO/readability tool: keyword density and Flesch reading ease."""
    words = _words(text)
    total = max(len(words), 1)
    lowered = text.lower()
    density = {}
    for kw in keywords:
        kw_l = kw.strip().lower()
        if kw_l:
            density[kw] = round(100 * lowered.count(kw_l) * len(kw_l.split()) / total, 2)
    sentences = max(len(re.findall(r"[.!?]+", text)), 1)
    syl = sum(_syllables(w) for w in words)
    flesch = 206.835 - 1.015 * (total / sentences) - 84.6 * (syl / total)
    return {
        "word_count": len(words),
        "keyword_density_pct": density,
        "missing_keywords": [k for k, v in density.items() if v == 0],
        "flesch_reading_ease": round(flesch, 1),
    }
