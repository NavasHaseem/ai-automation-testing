

from __future__ import annotations
from typing import Tuple
import io


import fitz
from docx import Document



class ParseError(Exception):

    pass

class UnsupportedFileTypeError(ParseError):
    def __init__(self, filename: str):
        super().__init__(f"Unsupported file type for '{filename}'. "
                         f"Supported: .pdf, .docx, .txt")

class EncryptedFileError(ParseError):
    def __init__(self, filename: str):
        super().__init__(f"File '{filename}' is encrypted/password-protected. "
                         f"Provide a decrypted version or handle password input.")

class EmptyTextError(ParseError):
    def __init__(self, filename: str):
        super().__init__(f"No extractable text found in '{filename}'. "
                         f"If this is a scanned PDF, enable OCR.")

class CorruptedFileError(ParseError):
    def __init__(self, filename: str, detail: str | None = None):
        msg = f"File '{filename}' appears corrupted or unreadable."
        if detail:
            msg += f" Details: {detail}"
        super().__init__(msg)



def extract_text_from_pdf(pdf_bytes: bytes, *, filename: str) -> Tuple[str, int]:

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:

            if doc.is_encrypted:

                try:
                    _ = doc[0].get_text("text")
                except Exception:
                    raise EncryptedFileError(filename)

            text_chunks = []
            for page in doc:
                text_chunks.append(page.get_text("text"))
            text = "\n".join(text_chunks)
            if not text.strip():

                raise EmptyTextError(filename)
            return text, len(text_chunks)
    except EncryptedFileError:
        raise
    except EmptyTextError:
        raise
    except fitz.FileDataError as e:

        raise CorruptedFileError(filename, detail=str(e)) from e
    except fitz.FileStructureError as e:
        raise CorruptedFileError(filename, detail=str(e)) from e
    except Exception as e:

        raise ParseError(f"Failed to extract text from PDF '{filename}': {e}") from e


def extract_text_from_docx(docx_bytes: bytes, *, filename: str) -> str:

    try:
        buf = io.BytesIO(docx_bytes)
        doc = Document(buf)
        text = "\n".join([p.text for p in doc.paragraphs]).strip()
        if not text:
            raise EmptyTextError(filename)
        return text
    except EmptyTextError:
        raise
    except Exception as e:
        raise ParseError(f"Failed to extract text from DOCX '{filename}': {e}") from e



def extract_text(filename: str, file_bytes: bytes) -> str:

    fname = filename.lower()


    if fname.endswith(".txt"):
        try:
            txt = file_bytes.decode("utf-8", errors="ignore").strip()
            if not txt:
                raise EmptyTextError(filename)
            return txt
        except Exception as e:
            raise ParseError(f"Failed to read TXT '{filename}': {e}") from e

    if fname.endswith(".pdf"):
        text, _ = extract_text_from_pdf(file_bytes, filename=filename)
        return text

    if fname.endswith(".docx"):
        return extract_text_from_docx(file_bytes, filename=filename)

