import re
import unicodedata


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation and accents for comparison."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[''`]", "", text)  # remove apostrophes
    text = re.sub(r"[^a-z0-9 ]", " ", text)  # non-alphanum to space
    text = re.sub(r"\s+", " ", text).strip()
    return text


def check_diagnosis(actual_name: str, submitted: str) -> bool:
    """Check if submitted diagnosis matches the actual disorder name.

    Uses exact match (case-insensitive) and fuzzy matching.
    Returns True for match, False for no match (caller should use LLM fallback).
    """
    norm_actual = _normalize(actual_name)
    norm_submitted = _normalize(submitted)

    if norm_actual == norm_submitted:
        return True

    if norm_submitted and norm_submitted in norm_actual:
        return True

    if norm_actual and norm_actual in norm_submitted:
        return True

    return False


def extract_diagnosis_tag(text: str) -> str | None:
    """Extract disorder name from [DIAGNOSIS: ...] tag in text."""
    match = re.search(r"\[DIAGNOSIS:\s*(.+?)\s*\]", text)
    if match:
        return match.group(1).strip()
    return None


def strip_diagnosis_tag(text: str) -> str:
    """Remove the [DIAGNOSIS: ...] wrapper from text, keeping the disorder name."""
    return re.sub(r"\[DIAGNOSIS:\s*(.+?)\s*\]", r"\1", text)


def build_llm_diagnosis_prompt(actual_name: str, submitted: str) -> str:
    """Build a prompt for LLM-based diagnosis equivalence check."""
    return (
        f"Is '{submitted}' the same neurological disorder as '{actual_name}'? "
        f"Consider synonyms, abbreviations, and alternate clinical terminology. "
        f"Reply with exactly 'YES' or 'NO'."
    )
