import fitz
from docx import Document


def extract_pdf_text(file):
    text = ""
    pdf = fitz.open(stream=file.read(), filetype="pdf")

    for page_number, page in enumerate(pdf, start=1):
        page_text = page.get_text()
        text += f"\n\n--- Page {page_number} ---\n{page_text}"

    return text.strip()


def extract_docx_text(file):
    document = Document(file)
    paragraphs = [para.text for para in document.paragraphs if para.text.strip()]
    return "\n".join(paragraphs)


def load_document(file):
    file_name = file.name.lower()

    if file_name.endswith(".pdf"):
        return extract_pdf_text(file)

    if file_name.endswith(".docx"):
        return extract_docx_text(file)

    raise ValueError("Unsupported file type")