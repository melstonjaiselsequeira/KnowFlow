
from pathlib import Path
import pymupdf
import pandas as pd
from zipfile import ZipFile
import xml.etree.ElementTree as ET


# 1. PDF extraction with page numbers
def extract_pdf_pages(file_path: str) -> list:
    pages = []

    with pymupdf.open(file_path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            page_text = page.get_text("text").strip()

            if page_text:
                pages.append({
                    "page_number": page_number,
                    "text": page_text
                })

    return pages


# Maintain the existing PDF extraction function
def extract_pdf(file_path: str) -> str:
    pages = extract_pdf_pages(file_path)

    return "\n".join(
        f"\n--- Page {page['page_number']} ---\n{page['text']}"
        for page in pages
    )


# 2. DOCX extraction
def extract_docx(file_path: str) -> str:
    namespace = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    }

    with ZipFile(file_path, "r") as docx:
        xml_content = docx.read("word/document.xml")

    root = ET.fromstring(xml_content)
    body = root.find("w:body", namespace)

    extracted_text = []

    for element in body:

        # Extract paragraphs
        if element.tag.endswith("}p"):
            paragraph = "".join(
                node.text or ""
                for node in element.findall(".//w:t", namespace)
            )

            if paragraph.strip():
                extracted_text.append(paragraph)

        # Extract tables
        elif element.tag.endswith("}tbl"):
            for row in element.findall(".//w:tr", namespace):
                cells = []

                for cell in row.findall("./w:tc", namespace):
                    cell_text = "".join(
                        node.text or ""
                        for node in cell.findall(".//w:t", namespace)
                    )

                    cells.append(cell_text)

                extracted_text.append(" | ".join(cells))

    return "\n".join(extracted_text)


# 3. CSV extraction
def extract_csv(file_path: str) -> str:
    dataframe = pd.read_csv(file_path)
    return dataframe.to_string(index=False)


# 4. TXT extraction
def extract_txt(file_path: str) -> str:
    return Path(file_path).read_text(
        encoding="utf-8",
        errors="replace"
    )


# 5. Structured extraction with source information
def extract_document_pages(file_path: str) -> list:
    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":
        return extract_pdf_pages(file_path)

    elif extension == ".docx":
        text = extract_docx(file_path)

    elif extension == ".csv":
        text = extract_csv(file_path)

    elif extension == ".txt":
        text = extract_txt(file_path)

    else:
        raise ValueError("Unsupported document format")

    if not text.strip():
        return []

    # Non-PDF documents currently have no reliable page mapping.
    return [{
        "page_number": None,
        "text": text
    }]


# 6. Existing general extraction function (backward compatible)
def extract_document(file_path: str) -> str:
    pages = extract_document_pages(file_path)

    extracted_text = []

    for page in pages:
        if page["page_number"] is not None:
            extracted_text.append(
                f"\n--- Page {page['page_number']} ---\n{page['text']}"
            )
        else:
            extracted_text.append(page["text"])

    return "\n".join(extracted_text)
