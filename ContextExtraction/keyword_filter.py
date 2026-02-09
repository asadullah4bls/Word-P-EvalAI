# ======================================================
# keyword_filter.py  (FINAL – AGGRESSIVE & EFFECTIVE)
# ======================================================

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from spellchecker import SpellChecker
import nltk
from nltk.corpus import stopwords
import spacy
import re

# ------------------------------------------------------
# SETUP
# ------------------------------------------------------
nltk.download("stopwords")
STOPWORDS = set(stopwords.words("english"))

spell = SpellChecker()
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer("all-MiniLM-L6-v2")

from ContextExtraction.keywords_text import extract_keywords_from_pdf

# ------------------------------------------------------
# CONFIG
# ------------------------------------------------------
TEXT_SIM_THRESHOLD = 0.65
DIAGRAM_SIM_THRESHOLD = 0.75
MIN_DIAGRAM_KEYWORDS = 5

MIN_WORD_LEN = 3
MAX_WORDS_IN_PHRASE = 4
SPELL_RATIO_THRESHOLD = 0.6   # 60% of words must be real

# ======================================================
# CORE SANITY CHECK (THIS IS THE KEY FIX)
# ======================================================
def is_sane_phrase(phrase: str) -> bool:
    words = phrase.split()
    if not words:
        return False

    # 1. Reject repeated words
    if len(words) != len(set(words)):
        return False

    # 2. Reject malformed tokens (trainingdata, abc123, ctr)
    for w in words:
        if not re.fullmatch(r"[a-z]{3,}", w):
            return False

    # 3. Spell-check majority of words
    correct = sum(1 for w in words if w in spell)
    if (correct / len(words)) < SPELL_RATIO_THRESHOLD:
        return False

    # 4. POS check → must contain NOUN
    doc = nlp(phrase)
    if not any(tok.pos_ in ("NOUN", "PROPN") for tok in doc):
        return False

    return True

# ======================================================
# FILTER FUNCTION
# ======================================================
def filter_keywords(keywords, threshold):
    if not keywords:
        return []

    candidates = []

    # -----------------------------
    # CLEAN + SANITY FILTER
    # -----------------------------
    for kw, _ in keywords:
        kw = kw.lower()
        kw = re.sub(r"[^a-z\s]", " ", kw)
        kw = re.sub(r"\s+", " ", kw).strip()

        tokens = [
            w for w in kw.split()
            if w not in STOPWORDS and len(w) >= MIN_WORD_LEN
        ]

        if not tokens or len(tokens) > MAX_WORDS_IN_PHRASE:
            continue

        phrase = " ".join(tokens)

        if not is_sane_phrase(phrase):
            continue

        candidates.append(phrase)

    if not candidates:
        return []

    # Remove exact duplicates
    candidates = list(dict.fromkeys(candidates))

    # -----------------------------
    # SEMANTIC DEDUPLICATION
    # -----------------------------
    embeddings = model.encode(candidates)
    sim_matrix = cosine_similarity(embeddings)

    kept = []
    kept_idx = []

    for i, kw in enumerate(candidates):
        if not kept:
            kept.append(kw)
            kept_idx.append(i)
            continue

        if all(sim_matrix[i][j] < threshold for j in kept_idx):
            kept.append(kw)
            kept_idx.append(i)

    return kept

# ======================================================
# MAIN ENTRY
# ======================================================
def get_filtered_keywords_from_pdf(pdf_path):
    raw_keywords = extract_keywords_from_pdf(pdf_path)
    if not raw_keywords:
        return []

    text_kws = []
    diagram_kws = []

    for kw, score, source in raw_keywords:
        if source == "diagram":
            diagram_kws.append((kw, score))
        else:
            text_kws.append((kw, score))

    filtered_text = filter_keywords(text_kws, TEXT_SIM_THRESHOLD)
    filtered_diagram = filter_keywords(diagram_kws, DIAGRAM_SIM_THRESHOLD)

    if len(filtered_diagram) < MIN_DIAGRAM_KEYWORDS:
        filtered_diagram = [kw for kw, _ in diagram_kws[:MIN_DIAGRAM_KEYWORDS]]

    return filtered_text + filtered_diagram

# ======================================================
# TEST
# ======================================================
if __name__ == "__main__":
    pdf_path = r"C:\BLS\EvalAI8\Uploads\Transformer_attention_3.pdf"

    final_keywords = get_filtered_keywords_from_pdf(pdf_path)

    print("\n=== FINAL FILTERED KEYWORDS ===")
    for kw in final_keywords:
        print(kw)

    print(f"\nTotal Keywords after filtering: {len(final_keywords)}")
