import fitz
from docx import Document


def extract_pdf_text(file):
    text = ""
    pdf = fitz.open(stream=file.read(), filetype="pdf")

    for page_number, page in enumerate(pdf, start=1):
        # "blocks" groups text by paragraph/layout block instead of raw line-by-line,
        # which preserves real paragraph breaks much better than page.get_text()
        blocks = page.get_text("blocks")
        # sort top-to-bottom, left-to-right
        blocks.sort(key=lambda b: (round(b[1], 1), b[0]))

        page_text = "\n\n".join(
            b[4].strip() for b in blocks if b[4].strip()
        )
        text += f"\n\n--- Page {page_number} ---\n{page_text}"

    return text.strip()


def extract_docx_text(file):
    document = Document(file)
    paragraphs = [para.text for para in document.paragraphs if para.text.strip()]
    # double newline = real paragraph/heading boundary, needed for section detection
    return "\n\n".join(paragraphs)


def load_document(file):
    file_name = file.name.lower()

    if file_name.endswith(".pdf"):
        return extract_pdf_text(file)

    if file_name.endswith(".docx"):
        return extract_docx_text(file)

    raise ValueError("Unsupported file type")