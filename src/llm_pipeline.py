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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

if not GEMINI_API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY not found. Add it to your .env file "
        "(see .env.example) before using llm_pipeline."
    )

client = genai.Client(api_key=GEMINI_API_KEY)

RESPONSE_SCHEMA: Dict[str, Any] = {
    "key_points": [],
    "novelty": "",
    "research_gap": "",
    "future_work": "",
    "conclusion_summary": "",
    "core_tech_tags": [],
}


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

    response = client.models.generate_content(
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
        response = client.models.generate_content(
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
    response = client.models.generate_content(
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

    response = client.models.generate_content(
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