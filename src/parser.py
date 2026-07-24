"""
parser.py
Section-aware parser: takes cleaned raw text and splits it into
title / abstract / sections{} / references[] using heading heuristics.
"""

import re

# Common academic paper section headings (extend as you test on more papers)
SECTION_HEADINGS = [
    "abstract",
    "introduction",
    "related work",
    "background",
    "literature review",
    "methodology",
    "methods",
    "materials and methods",
    "proposed method",
    "system design",
    "architecture",
    "experiments",
    "experimental setup",
    "results",
    "results and discussion",
    "discussion",
    "evaluation",
    "conclusion",
    "conclusions",
    "future work",
    "limitations",
    "acknowledgments",
    "references",
    "bibliography",
]

# Matches lines like: "1. Introduction", "II. RELATED WORK", "Abstract", "3.2 Methodology"
HEADING_PATTERN = re.compile(
    r"^\s*(?:[\dIVXLC]+\.?\d*\.?\s+)?(" + "|".join(SECTION_HEADINGS) + r")\s*$",
    re.IGNORECASE,
)


def _normalize(heading: str) -> str:
    return heading.strip().lower().replace(" ", "_")


def detect_sections(cleaned_text: str) -> dict:
    """
    Split cleaned_text into a dict of {section_name: section_text}.
    Falls back to putting everything under 'body' if no headings are found.
    """
    lines = cleaned_text.splitlines()

    matches = []  # (line_index, normalized_section_name)
    for i, line in enumerate(lines):
        m = HEADING_PATTERN.match(line)
        if m:
            matches.append((i, _normalize(m.group(1))))

    if not matches:
        return {"body": cleaned_text.strip()}

    sections = {}
    for idx, (line_idx, name) in enumerate(matches):
        start = line_idx + 1
        end = matches[idx + 1][0] if idx + 1 < len(matches) else len(lines)
        content = "\n".join(lines[start:end]).strip()
        # If a heading repeats (rare OCR artifact), keep the longer version
        if name in sections and len(sections[name]) >= len(content):
            continue
        sections[name] = content

    return sections


def extract_title(cleaned_text: str, max_lines: int = 5) -> str:
    """
    Naive title guess: first non-empty line before any detected heading.
    Works for most arXiv/DOCX exports where the title is the first line.
    """
    for line in cleaned_text.splitlines()[:max_lines]:
        line = line.strip()
        if line and not HEADING_PATTERN.match(line):
            return line
    return ""


def extract_references(sections: dict) -> list:
    """
    Split the 'references' section into a list of individual reference strings.
    Handles common formats: numbered [1], 1., or blank-line separated entries.
    """
    ref_text = sections.get("references") or sections.get("bibliography")
    if not ref_text:
        return []

    # Try splitting on numbered reference markers like "[1]" or "1."
    entries = re.split(r"\n(?=\[\d+\]|\d{1,3}\.\s)", ref_text.strip())
    entries = [e.strip() for e in entries if e.strip()]
    return entries


def parse_document(cleaned_text: str) -> dict:
    """
    Main entry point: produces the structured JSON shape from your roadmap:
    {title, abstract, sections: {...}, references: [...]}
    """
    sections = detect_sections(cleaned_text)
    title = extract_title(cleaned_text)
    abstract = sections.pop("abstract", "")
    references = extract_references(sections)
    sections.pop("references", None)
    sections.pop("bibliography", None)

    return {
        "title": title,
        "abstract": abstract,
        "sections": sections,
        "references": references,
    }