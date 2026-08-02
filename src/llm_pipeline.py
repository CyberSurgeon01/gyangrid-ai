"""
src/llm_pipeline.py

Phase 4 — LLM Prompting Pipeline for GyanGrid AI.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Union

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

if not GEMINI_API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY not found. Add it to your .env file "
        "(see .env.example) before using llm_pipeline."
    )

client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            initial_delay=1.0,
            attempts=3,
            max_delay=20.0,
            exp_base=2,
            # 429 deliberately excluded: Google's SDK ignores the server's
            # actual suggested retry_delay for 429s and uses its own fixed
            # backoff instead, which is often too short. We handle 429s
            # ourselves in _call_with_quota_retry() below using the real
            # delay Gemini reports, instead of guessing.
            http_status_codes=[408, 500, 502, 503, 504],
        ),
        timeout=180 * 1000,
    ),
)

_MAX_MANUAL_RETRY_WAIT = 90  # don't block a Streamlit request longer than this


def _is_quota_exception(e: Exception) -> bool:
    msg = str(e).lower()
    return "429" in msg or "resource_exhausted" in msg or "quota" in msg


def is_zero_quota_exception(e: Exception) -> bool:
    """True when Gemini's error indicates a hard 0-quota allocation on this
    API key/project (e.g. '"limit": 0' in a QuotaFailure violation, usually
    a free-tier project with no billing enabled) rather than a transient
    per-minute rate limit. In this case Gemini's 'retry in Ns' hint is just
    its generic 429 backoff and is meaningless — retrying will fail the
    exact same way every time until quota/billing is actually fixed, so
    callers should show a different message and skip the retry-and-sleep."""
    msg = str(e)
    return bool(re.search(r"['\"]?limit['\"]?\s*:\s*0\b", msg))


def _call_with_quota_retry(fn, *args, **kwargs):
    """Calls fn(*args, **kwargs) — a client.models.generate_content call —
    and if it fails with a real quota/429 error, reads Gemini's own
    suggested wait time from the error and sleeps that exact amount
    before retrying once. Falls back to raising the original error if
    there's no usable delay, the delay is too long to reasonably block
    on, the account has a hard 0-quota allocation (retrying can't help),
    or the retry also fails."""
    import time
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        if not _is_quota_exception(e):
            raise
        if is_zero_quota_exception(e):
            raise  # zero quota won't refill in a few seconds — don't bother retrying
        wait_s = extract_retry_seconds(e)
        if wait_s is None or wait_s > _MAX_MANUAL_RETRY_WAIT:
            raise
        time.sleep(wait_s + 1)  # +1s buffer past the server's own estimate
        return fn(*args, **kwargs)  # let this one raise naturally if it fails too

RESPONSE_SCHEMA: Dict[str, Any] = {
    "key_points": [],
    "novelty": "",
    "research_gap": "",
    "future_work": "",
    "conclusion_summary": "",
    "core_tech_tags": [],
}


def extract_retry_seconds(e: Exception) -> Optional[float]:
    """Parses Gemini's real suggested retry delay out of a 429 error's
    message (e.g. '...Please retry in 53.016342224s.') so callers can
    show an accurate wait time instead of a guess. Returns None if no
    such hint is present in the error text."""
    match = re.search(r"retry in ([\d.]+)s", str(e), re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _chunks_to_text(chunks: List[Union[str, Dict[str, Any]]]) -> str:
    parts = []
    for c in chunks:
        if isinstance(c, dict):
            section = c.get("section", "unknown")
            text = c.get("text", "")
            parts.append(f"[Section: {section}]\n{text}")
        else:
            parts.append(str(c))
    return "\n\n---\n\n".join(parts)


def _build_prompt(chunks_by_type, language, word_limit):
    lang_instruction = (
        "Write ALL string values in Bangla (bn), using natural academic Bangla."
        if language == "bn"
        else "Write ALL string values in English."
    )

    word_limit_instruction = (
        f"Keep 'conclusion_summary' to roughly {word_limit} words or fewer."
        if word_limit
        else "Keep 'conclusion_summary' concise (around 100-150 words)."
    )

    novelty_text = _chunks_to_text(chunks_by_type.get("novelty", []))
    gap_text = _chunks_to_text(chunks_by_type.get("research_gap", []))
    future_text = _chunks_to_text(chunks_by_type.get("future_work", []))
    general_text = _chunks_to_text(chunks_by_type.get("general", []))

    prompt = f"""You are analyzing an academic research paper based on retrieved excerpts below.
Return ONLY a single valid JSON object — no markdown fences, no preamble, no commentary.

The JSON object MUST have exactly these keys:
- "key_points": array of 3-6 short strings, the paper's main takeaways
- "novelty": string, what is new/original about this paper
- "research_gap": string, what gap in existing research this paper addresses
- "future_work": string, what future work the authors suggest or that is implied
- "conclusion_summary": string, a summary of the paper's conclusion
- "core_tech_tags": array of 3-8 short strings, key techniques/technologies/methods used

{lang_instruction}
{word_limit_instruction}
If an excerpt section below is empty or not relevant, infer that field as best you can
from the "General excerpts" section instead. Never leave a field as null — use an empty
string or empty array if truly no information is available.

--- Excerpts relevant to NOVELTY ---
{novelty_text or "(none retrieved)"}

--- Excerpts relevant to RESEARCH GAP ---
{gap_text or "(none retrieved)"}

--- Excerpts relevant to FUTURE WORK ---
{future_text or "(none retrieved)"}

--- General excerpts (title, abstract, key sections) ---
{general_text or "(none retrieved)"}

Return the JSON object now.
"""
    return prompt


def _extract_json(raw_text: str) -> Dict[str, Any]:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Gemini did not return valid JSON. Raw response:\n{raw_text}"
        ) from e


def _expand_query(query: str) -> str:
    """
    Expand short or vague queries with semantic keywords so FAISS
    retrieves the right section chunks instead of unrelated ones.
    """
    q_lower = query.lower()

    if any(kw in q_lower for kw in ["future", "upcoming", "next", "scope", "recommend"]):
        return f"future work directions recommendations scope limitations {query}"

    if any(kw in q_lower for kw in ["gap", "missing", "problem", "challenge", "issue", "limitation"]):
        return f"research gap problem statement prior work limitation {query}"

    if any(kw in q_lower for kw in ["novel", "new", "contribution", "propose", "introduce", "original"]):
        return f"novelty original contribution proposed method {query}"

    if any(kw in q_lower for kw in ["method", "approach", "technique", "model", "architecture", "how"]):
        return f"methodology approach proposed model architecture {query}"

    if any(kw in q_lower for kw in ["result", "performance", "accuracy", "score", "evaluation", "experiment"]):
        return f"results evaluation performance accuracy experiment benchmark {query}"

    if any(kw in q_lower for kw in ["dataset", "data", "corpus", "annotation", "collection"]):
        return f"dataset corpus data collection annotation statistics {query}"

    if any(kw in q_lower for kw in ["conclusion", "summary", "finding", "takeaway"]):
        return f"conclusion summary findings key takeaways {query}"

    # No expansion needed — query is already specific enough
    return query


def analyze_paper(chunks_by_type, language="en", word_limit=None, model_name=None):
    if language not in ("en", "bn"):
        raise ValueError("language must be 'en' or 'bn'")

    prompt = _build_prompt(chunks_by_type, language, word_limit)

    response = _call_with_quota_retry(
        client.models.generate_content,
        model=model_name or GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )

    result = _extract_json(response.text)

    for key, default in RESPONSE_SCHEMA.items():
        result.setdefault(key, default)

    return result


COMPARE_SECTIONS = (
    "novelty", "research_gap", "methodology", "results", "future_work", "conclusion",
)

COMPARE_RESPONSE_SCHEMA: Dict[str, Any] = {
    "paper_a": {sec: [] for sec in COMPARE_SECTIONS},
    "paper_b": {sec: [] for sec in COMPARE_SECTIONS},
    "insight": {sec: "" for sec in COMPARE_SECTIONS},
    "verdict": {
        "overall_similarity": 0,
        "better_novelty": "",
        "better_methodology": "",
        "better_results": "",
        "future_potential": "",
        "overall_winner": "",
        "overall_winner_reason": "",
    },
}


def _build_compare_prompt(paper_a_title, paper_a_sections, paper_b_title, paper_b_sections, language):
    lang_instruction = (
        "Write ALL string values in Bangla (bn), using natural academic Bangla."
        if language == "bn"
        else "Write ALL string values in English."
    )

    def _section_block(sections: dict) -> str:
        blocks = []
        for sec in COMPARE_SECTIONS:
            text = _chunks_to_text(sections.get(sec, []))
            blocks.append(f"--- {sec.upper()} ---\n{text or '(none retrieved)'}")
        return "\n\n".join(blocks)

    prompt = f"""You are comparing two academic research papers section by section using the
retrieved excerpts below. Return ONLY a single valid JSON object — no markdown fences,
no preamble, no commentary.

The JSON object MUST have exactly these top-level keys: "paper_a", "paper_b", "insight", "verdict".

For "paper_a" and "paper_b": each is an object with exactly these keys, one per comparison
section: {', '.join(COMPARE_SECTIONS)}. Each value is an array of 3-6 short bullet-point
strings summarizing that paper's content for that section, based only on the excerpts given.
If a section has no relevant excerpts, infer a best-effort bullet from context, or return an
empty array if nothing can be reasonably inferred.

For "insight": an object with the same section keys, each a 1-3 sentence string comparing
the two papers specifically for that section (what's similar, what differs, which is stronger
and why).

For "verdict": an object with exactly these keys:
- "overall_similarity": integer 0-100, how similar the two papers are overall
- "better_novelty": "Paper A", "Paper B", or "Tie"
- "better_methodology": "Paper A", "Paper B", or "Tie"
- "better_results": "Paper A", "Paper B", or "Tie"
- "future_potential": "Paper A", "Paper B", or "Tie"
- "overall_winner": "Paper A", "Paper B", or "Tie"
- "overall_winner_reason": one short sentence explaining the overall winner choice

{lang_instruction}
Never leave a field as null — use an empty string, empty array, or "Tie" as appropriate.

======================
PAPER A: {paper_a_title or "Untitled"}
======================
{_section_block(paper_a_sections)}

======================
PAPER B: {paper_b_title or "Untitled"}
======================
{_section_block(paper_b_sections)}

Return the JSON object now.
"""
    return prompt


def compare_papers(paper_a_title: str, paper_a_sections: dict,
                    paper_b_title: str, paper_b_sections: dict,
                    language: str = "en", model_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Compares two papers section-by-section (novelty, research_gap, methodology,
    results, future_work, conclusion) and returns per-paper bullet points, a
    per-section AI insight, and an overall verdict — mirroring analyze_paper()'s
    shape/contract so callers (compare_page.py) can use it the same way.

    paper_a_sections / paper_b_sections: dicts keyed by COMPARE_SECTIONS, each
    value a list of retrieved chunks (same shape analyze_paper() expects per key,
    i.e. str or {"section":..., "text":...} dicts).
    """
    if language not in ("en", "bn"):
        raise ValueError("language must be 'en' or 'bn'")

    prompt = _build_compare_prompt(paper_a_title, paper_a_sections, paper_b_title, paper_b_sections, language)

    response = _call_with_quota_retry(
        client.models.generate_content,
        model=model_name or GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )

    result = _extract_json(response.text)

    # Fill in any missing keys defensively, same pattern as analyze_paper().
    result.setdefault("paper_a", {})
    result.setdefault("paper_b", {})
    result.setdefault("insight", {})
    result.setdefault("verdict", {})
    for sec in COMPARE_SECTIONS:
        result["paper_a"].setdefault(sec, [])
        result["paper_b"].setdefault(sec, [])
        result["insight"].setdefault(sec, "")
    for key, default in COMPARE_RESPONSE_SCHEMA["verdict"].items():
        result["verdict"].setdefault(key, default)

    return result


def classify_is_research_paper(text: str) -> Dict[str, Any]:
    """
    Semantic fallback check for src/paper_validator.py — only called for
    documents whose structural heuristic score is borderline (an obvious
    paper or an obvious non-paper never needs this network call).

    Returns {"is_paper": bool, "reason": str}. Deliberately does NOT raise
    on a malformed model response — paper_validator.py treats a failure
    here as "unavailable" and falls back to the heuristic score rather
    than blocking the upload on a transient API issue.
    """
    prompt = f"""You are a classifier deciding whether the text below is from an
academic/scientific research paper (journal article, conference paper, preprint,
thesis chapter, technical report with citations, etc.) as opposed to something
else entirely (resume, invoice, blog post, news article, slide deck export,
personal notes, marketing material, etc.).

Return ONLY a single valid JSON object — no markdown fences, no preamble.
The JSON object MUST have exactly these keys:
- "is_paper": boolean
- "reason": string, one short sentence explaining the decision

Base your judgment on writing register, presence of academic structure
(abstract-like framing, methodology, citations, findings), and subject
matter — not on formatting artifacts from PDF extraction.

--- TEXT SAMPLE ---
{text}
--- END SAMPLE ---

Return the JSON object now.
"""

    try:
        response = _call_with_quota_retry(
            client.models.generate_content,
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        result = _extract_json(response.text)
        return {
            "is_paper": bool(result.get("is_paper")),
            "reason": str(result.get("reason", "")),
        }
    except Exception as e:
        return {"is_paper": None, "reason": f"classification failed: {e}"}


def translate_summary(text: str, target_language: str = "bn") -> str:
    lang_name = "Bangla" if target_language == "bn" else target_language
    prompt = (
        f"Translate the following academic text into natural, fluent {lang_name}. "
        f"Return ONLY the translated text, nothing else.\n\n{text}"
    )
    response = _call_with_quota_retry(
        client.models.generate_content,
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text.strip()


def answer_question(query: str, retrieved_chunks: list, language: str = "en") -> str:
    """
    Takes a user question and the RAG-retrieved chunks, and asks Gemini to
    synthesize a direct, grounded answer instead of just showing raw excerpts.

    Query expansion is handled upstream (in app.py or via _expand_query),
    so this function receives already-retrieved chunks and focuses on synthesis.
    """
    if not retrieved_chunks:
        if language == "bn":
            return "এই প্রশ্নের জন্য কাগজে কোনো প্রাসঙ্গিক বিষয়বস্তু পাওয়া যায়নি।"
        return "No relevant content found in the paper for this question."

    context_text = _chunks_to_text(retrieved_chunks)

    lang_instruction = (
        "Answer in natural academic Bangla (Bengali script)."
        if language == "bn"
        else "Answer in clear English."
    )

    prompt = f"""You are answering a question about a research paper using the excerpts below.
Give a direct, well-organized answer in 2-5 sentences. Synthesize the excerpts — do not repeat them verbatim.
If the excerpts are not directly about the question but contain related information, use that to give
the best possible answer and clearly note what you inferred from context.
Only say "not enough information" if the excerpts are completely unrelated to the question.

{lang_instruction}

Question: {query}

Excerpts:
{context_text}

Answer:"""

    response = _call_with_quota_retry(
        client.models.generate_content,
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2),
    )
    return response.text.strip()


if __name__ == "__main__":
    # Quick smoke test
    sample_chunks = {
        "novelty": ["This paper introduces a novel Bangla idiom detection dataset..."],
        "research_gap": ["Prior work has largely ignored figurative language in Bangla NLP..."],
        "future_work": ["Future work includes expanding the dataset to spoken corpora..."],
        "general": ["Title: Bangla Idiom Detection via Contextual Embeddings. Abstract: ..."],
    }
    result = analyze_paper(sample_chunks, language="en", word_limit=120)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Test query expansion
    test_query = "what is the future"
    expanded = _expand_query(test_query)
    print(f"\nOriginal query: '{test_query}'")
    print(f"Expanded query: '{expanded}'")