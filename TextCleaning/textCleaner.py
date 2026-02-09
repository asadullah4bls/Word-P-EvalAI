import fitz  # PyMuPDF
import re

def extract_clean_text(pdf_path: str) -> str:
    """Extracts and cleans text from a PDF for keyword extraction and quiz generation."""

    # ----------------------------
    # 1. Extract text page-wise
    # ----------------------------
    doc = fitz.open(pdf_path)
    pages_text = [page.get_text("text") for page in doc]
    doc.close()
    full_text = "\n".join(pages_text)

    # ----------------------------
    # 2. Remove repeated headers / footers
    # ----------------------------
    lines = [l.strip() for l in full_text.split("\n")]
    freq = {}
    for line in lines:
        if len(line) < 4:
            continue
        freq[line] = freq.get(line, 0) + 1
    lines = [l for l in lines if freq.get(l, 0) < 3]

    # ----------------------------
    # 3. Remove emails on page 1 only
    # ----------------------------
    if len(lines) > 0:
        first_page_lines = lines[:100]
        first_page_lines = [re.sub(r"\S+@\S+", "", l) for l in first_page_lines]
        lines[:100] = first_page_lines

    text = "\n".join(lines)

    # ----------------------------
    # 4. Remove TOC / Lists (robust)
    # ----------------------------
    text = re.sub(
        r"(table of contents|contents|list of figures|list of tables)"
        r"(.|\n){0,1500}",
        "",
        text,
        flags=re.IGNORECASE
    )

    # ----------------------------
    # 5. Remove References / Bibliography / Appendix
    # ----------------------------
    text = re.sub(
        r"\n(references|bibliography|works cited|appendix)\b(.|\n)*$",
        "",
        text,
        flags=re.IGNORECASE
    )

    # ----------------------------
    # 6. Remove page numbers
    # ----------------------------
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"page\s*\d+(\s*of\s*\d+)?", "", text, flags=re.IGNORECASE)

    # ----------------------------
    # 7. Remove citation numbers like [1], [2,3]
    # ----------------------------
    text = re.sub(r"\[\d+(,\s*\d+)*\]", "", text)

    # ----------------------------
    # 8. Fix hyphenated line breaks and merge broken lines
    # ----------------------------
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # ----------------------------
    # 9. Remove bullet symbols
    # ----------------------------
    text = re.sub(r"[•▪●◦]", "", text)

    # ----------------------------
    # 10. Normalize punctuation
    # ----------------------------
    text = (
        text.replace("–", "-")
            .replace("—", "-")
            .replace("“", '"')
            .replace("”", '"')
    )

    # ----------------------------
    # 11. Clean extra spaces
    # ----------------------------
    text = re.sub(r"[ \t]{2,}", " ", text)

    # ----------------------------
    # 12. Remove non-ASCII noise
    # ----------------------------
    text = re.sub(r"[^\x00-\x7F]+", " ", text)

    # ----------------------------
    # 13. START FROM MAIN CONTENT (FIXED)
    # ----------------------------
    START_PATTERNS = [
        r"\bchapter\s+1\b",
        r"\b1\.\s+introduction\b",
        r"\bintroduction\b",
        r"\bi\.\s+introduction\b"
    ]

    def find_main_start(text):
        for pattern in START_PATTERNS:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.start()
        return 0  # fallback if nothing found

    start_idx = find_main_start(text)
    text = text[start_idx:]

    # ----------------------------
    # 14. Final cleanup of newlines
    # ----------------------------
    text = re.sub(r"\n{2,}", "\n\n", text).strip()
    return text


if __name__ == "__main__":
    test_pdf_path = r"C:\BLS\EvalAI8\Uploads\cys_Secl.pdf"
    cleaned_text = extract_clean_text(test_pdf_path)
    print("----- Cleaned Text Output -----\n")
    print(cleaned_text)
