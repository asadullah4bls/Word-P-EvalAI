# keyword_extractor/context.py

import spacy
from collections import Counter

# --------------------------------------------------
# PROJECT IMPORTS
# --------------------------------------------------
from TextCleaning.textCleaner import extract_clean_text
from TextCleaning.diagramText import extract_from_pdf
from TextCleaning.table import extract_meaningful_tables

# --------------------------------------------------
# NLP MODEL
# --------------------------------------------------
nlp = spacy.load("en_core_web_sm")

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
TEXT_TOP_N = 30
DIAGRAM_TOP_N = 20

MIN_PHRASE_LEN = 2        # minimum words in phrase
MAX_PHRASE_LEN = 5        # safety cap

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def extract_noun_phrases(text: str):
    """
    Extract clean noun phrases from text.
    """
    doc = nlp(text)
    phrases = []

    for chunk in doc.noun_chunks:
        phrase = chunk.text.lower().strip()

        words = phrase.split()

        # length constraints
        if len(words) < MIN_PHRASE_LEN or len(words) > MAX_PHRASE_LEN:
            continue

        # must contain a noun/proper noun
        if not any(tok.pos_ in ("NOUN", "PROPN") for tok in chunk):
            continue

        # remove phrases starting or ending with stopwords
        if chunk[0].is_stop or chunk[-1].is_stop:
            continue

        phrases.append(phrase)

    return phrases


def rank_phrases(phrases, top_n):
    """
    Rank phrases by frequency.
    """
    freq = Counter(phrases)
    return freq.most_common(top_n)


# --------------------------------------------------
# MAIN FUNCTION
# --------------------------------------------------
def extract_keywords_from_pdf(pdf_path):
    """
    Extract keywords using linguistically valid noun phrases.
    """

    # ===============================
    # STEP 1: CLEAN TEXT
    # ===============================
    clean_text = extract_clean_text(pdf_path) or ""

    # ===============================
    # STEP 1B: TABLES
    # ===============================
    tables_text = extract_meaningful_tables(pdf_path) or ""

    if tables_text.strip():
        print("\n[✓] Tables extracted and merged")
        clean_text = clean_text + "\n\n" + tables_text

    # ===============================
    # STEP 2: DIAGRAM OCR TEXT
    # ===============================
    diagrams_list = extract_from_pdf(pdf_path)

    if isinstance(diagrams_list, list):
        diagrams_text = "\n".join(diagrams_list)
    else:
        diagrams_text = diagrams_list or ""

    final_keywords = {}

    # ===============================
    # STEP 3: TEXT KEYWORDS (NOUN PHRASES)
    # ===============================
    if clean_text.strip():
        print("\n[✓] Extracting keywords from MAIN TEXT (noun phrases)...")

        text_phrases = extract_noun_phrases(clean_text)
        ranked_text = rank_phrases(text_phrases, TEXT_TOP_N)

        for phrase, count in ranked_text:
            final_keywords[phrase] = {
                "score": float(count),
                "source": "text"
            }

    # ===============================
    # STEP 4: DIAGRAM KEYWORDS
    # ===============================
    if diagrams_text.strip():
        print("\n[✓] Extracting keywords from DIAGRAM TEXT (noun phrases)...")

        diagram_phrases = extract_noun_phrases(diagrams_text)
        ranked_diagram = rank_phrases(diagram_phrases, DIAGRAM_TOP_N)

        for phrase, count in ranked_diagram:
            if phrase not in final_keywords or count > final_keywords[phrase]["score"]:
                final_keywords[phrase] = {
                    "score": float(count),
                    "source": "diagram"
                }

    # ===============================
    # STEP 5: SORT OUTPUT
    # ===============================
    merged_keywords = sorted(
        [(kw, meta["score"], meta["source"]) for kw, meta in final_keywords.items()],
        key=lambda x: x[1],
        reverse=True
    )

    # ===============================
    # STEP 6: LOG OUTPUT
    # ===============================
    print("\n══════════ FINAL KEYWORDS ══════════")
    for kw, score, source in merged_keywords:
        print(f"{kw} | {source} | freq: {score}")

    print(f"\nTotal Keywords Extracted: {len(merged_keywords)}")
    print("════════════════════════════════════\n")

    return merged_keywords


# --------------------------------------------------
# TEST
# --------------------------------------------------
if __name__ == "__main__":
    test_pdf_path = r"C:\BLS_Live_Projects\AI-Quiz-Generator-Microservice\Uploads\AI_in_Healthcare_Paper.pdf"
    extract_keywords_from_pdf(test_pdf_path)
