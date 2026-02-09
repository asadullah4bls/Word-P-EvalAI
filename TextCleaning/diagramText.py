import fitz  # PyMuPDF
from typing import List
import easyocr
import numpy as np
from sklearn.cluster import DBSCAN
from collections import defaultdict
import cv2
import re

# ---------------------------------------
# GLOBAL: Load EasyOCR reader only once.
# ---------------------------------------
OCR_READER = easyocr.Reader(['en'], gpu=True)

def clean_ocr_text(text: str) -> str:
    """
    Cleans OCR-extracted diagram text by removing garbage tokens
    while preserving meaningful phrases.
    """
    if not text:
        return ""

    text = text.lower().strip()

    # Remove tokens with symbols or digits
    if re.search(r"[^a-z\s]", text):
        return ""

    words = text.split()

    # Must have at least 2 words
    if len(words) < 2:
        return ""

    clean_words = []
    for w in words:
        # length check
        if len(w) < 3:
            continue

        # must contain vowel
        if not re.search(r"[aeiou]", w):
            continue

        # only alphabetic
        if not w.isalpha():
            continue

        clean_words.append(w)

    # Require at least 2 valid words after cleaning
    if len(clean_words) < 2:
        return ""

    return " ".join(clean_words)

def get_eps_for_image(width, height):
    """
    Determine DBSCAN eps based on image size.
    Small images -> smaller eps
    Large images -> larger eps
    """
    print(f"Image dimensions: width={width}, height={height}")
    # You can tune these thresholds
    min_dim = min(width, height)
    if min_dim < 600:
        return 40
    elif min_dim < 900:
        return 80
    else:
        return 120


def extract_from_pdf(pdf_path: str, min_width=150, min_height=150) -> List[str]:
    """
    Faster optimized version:
    - Avoids re-creating EasyOCR reader
    - Skips unnecessary decoding
    - Reduces OpenCV overhead
    - Keeps all functionality identical
    """
    doc = fitz.open(pdf_path)
    extracted_texts = []

    print(f"\n[INFO] Processing PDF: {pdf_path}")

    for page_index, page in enumerate(doc):
        image_list = page.get_images(full=True)

        if not image_list:
            continue

        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)

            width = base_image.get("width", 0)
            height = base_image.get("height", 0)

            # Skip small images
            if width < min_width or height < min_height:
                continue

            img_bytes = base_image["image"]

            # very fast skip if image is invalid
            if not img_bytes:
                continue

            # Convert bytes → numpy → OpenCV
            img_np = np.frombuffer(img_bytes, np.uint8)
            img_cv = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

            if img_cv is None:
                continue

            # OCR with bounding boxes
            ocr_results = OCR_READER.readtext(img_cv, detail=1)

            if not ocr_results:
                continue

            # Extract bounding boxes + text
            boxes = []
            for (bbox, text, conf) in ocr_results:
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                boxes.append((min(xs), min(ys), max(xs), max(ys), text))

            if not boxes:
                continue

            # Cluster based on top-left coords
            coords = np.array([[b[0], b[1], b[2], b[3]] for b in boxes])
            
            # Adaptive eps
            eps_value = get_eps_for_image(width, height)
            labels = DBSCAN(eps=eps_value, min_samples=1).fit(coords).labels_

            groups = defaultdict(list)
            for idx, label in enumerate(labels):
                groups[label].append(boxes[idx])

            # Extract text cluster-by-cluster
            for label, group in groups.items():
                sorted_group = sorted(group, key=lambda b: (b[1], b[0]))
                raw_cluster_text = " ".join([b[4] for b in sorted_group]).strip()
                cleaned_cluster_text = clean_ocr_text(raw_cluster_text)
                if cleaned_cluster_text:
                    extracted_texts.append(cleaned_cluster_text)

            print(f"[✓] Extracted clustered text from diagram p{page_index + 1}-{img_index + 1}")

    doc.close()
    return "\n".join(extracted_texts)


if __name__ == "__main__":
    extracted_text = extract_from_pdf(
        r"C:\BLS\EvalAI8\Uploads\ai table based .pdf"
    )
    print("\nExtracted Diagram Text:", extracted_text)
