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
    "data description",
    "value of the data",
    "specifications table",
    "data collection",
    "annotation process",
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
    "ethics statement",
    "declaration of competing interest",
    "acknowledgments",
    "acknowledgements",
    "funding statement",
    "author contributions",
    "reference",
    "references",
    "bibliography",
]

# Matches lines like: "1. Introduction", "II. RELATED WORK", "Abstract", "3.2 Methodology"
HEADING_PATTERN = re.compile(
    r"^\s*(?:[\dIVXLC]+\.?\d*\.?\s+)?(" + "|".join(SECTION_HEADINGS) + r")\s*[:.]?\s*(.*)$",
    re.IGNORECASE,
)


def _normalize(heading: str) -> str:
    return heading.strip().lower().replace(" ", "_")


def detect_sections(cleaned_text: str) -> dict:
    """
    Split cleaned_text into a dict of {section_name: section_text}.
    Handles both:
      - heading alone on its own line
      - heading followed by content on the same line
    """
    lines = cleaned_text.splitlines()

    matches = []
    for i, line in enumerate(lines):
        m = HEADING_PATTERN.match(line)
        if m:
            heading, trailing = m.group(1), m.group(2)
            matches.append((i, _normalize(heading), trailing.strip()))

    if not matches:
        return {"body": cleaned_text.strip()}

    sections = {}
    for idx, (line_idx, name, trailing) in enumerate(matches):
        start = line_idx + 1
        end = matches[idx + 1][0] if idx + 1 < len(matches) else len(lines)
        content = "\n".join(lines[start:end]).strip()
        if trailing:
            content = (trailing + "\n" + content).strip()
        if name in sections and len(sections[name]) >= len(content):
            continue
        sections[name] = content

    return sections


def extract_title(cleaned_text: str, max_lines: int = 5) -> str:
    """
    Naive title guess: first non-empty line before any detected heading.
    """
    for line in cleaned_text.splitlines()[:max_lines]:
        line = line.strip()
        if line and not HEADING_PATTERN.match(line):
            return line
    return ""


def extract_references(sections: dict) -> list:
    """
    Split the references section into a list of individual reference strings.
    Handles "references", "reference" (singular), and "bibliography" headings.
    """
    ref_text = (
        sections.get("references")
        or sections.get("reference")
        or sections.get("bibliography")
    )
    if not ref_text:
        return []

    entries = re.split(r"\n(?=\[\d+\]|\d{1,3}\.\s)", ref_text.strip())
    entries = [e.strip() for e in entries if e.strip()]
    return entries


def parse_document(cleaned_text: str) -> dict:
    """
    Main entry point: produces the structured JSON shape:
    {title, abstract, sections: {...}, references: [...]}
    """
    sections = detect_sections(cleaned_text)
    title = extract_title(cleaned_text)
    abstract = sections.pop("abstract", "")
    references = extract_references(sections)
    sections.pop("references", None)
    sections.pop("reference", None)
    sections.pop("bibliography", None)

    return {
        "title": title,
        "abstract": abstract,
        "sections": sections,
        "references": references,
    }