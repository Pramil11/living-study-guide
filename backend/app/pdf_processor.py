import fitz


def extract_pdf_pages(file_path: str):
    pages = []

    with fitz.open(file_path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()

            pages.append({
                "page_number": page_number,
                "text": text,
                "character_count": len(text)
            })

    return pages