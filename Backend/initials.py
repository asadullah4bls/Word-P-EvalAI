# from langdetect import detect, LangDetectException
from PyPDF2 import PdfReader
import pdfplumber
import os
import re
from Backend.languageCheck import EnglishLanguageDetector

def is_english_file(file):
    """
    Check if uploaded PDF file contains predominantly English text.
    Intelligently samples pages from the middle to avoid front matter bias.
    Image-based PDFs are automatically accepted (no language check needed).
    
    Args:
        file: FileStorage object from Flask request
        
    Returns:
        bool: True if file is in English or image-based, False otherwise
    """
    try:
        # Save current position
        file.seek(0)
        
        # Read PDF content
        pdf_reader = PdfReader(file)
        total_pages = len(pdf_reader.pages)
        text = ""
        image_found = False
        
        print(f"📚 Analyzing PDF: {file.filename} ({total_pages} pages)")
        
        # Strategy: Sample pages based on document length
        if total_pages == 1:
            # Single page document - check that page
            pages_to_check = [0]
            print("   Strategy: Single page document")
            
        elif total_pages == 2:
            # Two page document - check both pages
            pages_to_check = [0, 1]
            print("   Strategy: Checking both pages")
            
        elif total_pages <= 10:
            # Short document (3-10 pages) - check middle pages
            # Skip first page (likely title/intro), check 2-3 middle pages
            start_idx = 1
            end_idx = min(total_pages, 4)
            pages_to_check = list(range(start_idx, end_idx))
            print(f"   Strategy: Short doc - checking pages {pages_to_check}")
            
        else:
            # Long document (11+ pages) - sample from middle third
            # This avoids: intro, TOC, abstract, index, references
            middle_start = total_pages // 3
            middle_end = (total_pages * 2) // 3
            
            # Select 3 pages from the middle section
            pages_to_check = [
                middle_start,
                (middle_start + middle_end) // 2,
                middle_end - 1
            ]
            print(f"   Strategy: Long doc - sampling middle pages {pages_to_check} (from middle third)")
        
        # Extract text from selected pages and check for images
        with pdfplumber.open(file) as pdf:
            for page_num in pages_to_check:
                if page_num < len(pdf.pages):
                    page = pdf.pages[page_num]
                    page_text = page.extract_text() or ""
                    text += page_text
                    print(f"   Page {page_num + 1}: {len(page_text)} characters extracted")
                    
                    # Check if page has images (scanned/image-based content)
                    if page.images:
                        image_found = True
                        print(f"   Page {page_num + 1}: Contains {len(page.images)} image(s)")
        
        # Reset file pointer
        file.seek(0)
        
        # If no text extracted, check if it's an image-based document
        if not text.strip():
            if image_found:
                print(f"✅ Image-based PDF detected (no text): {file.filename}")
                print(f"   Result: ACCEPTED (image-only document)\n")
                return True  # Accept image-only PDFs
            else:
                print(f"⚠️ No text or images extracted from PDF: {file.filename}")
                return False
        
        print(f"   Total text extracted: {len(text)} characters")
        
        # Use the detector class
        detector = EnglishLanguageDetector(
            english_threshold=0.80,
            max_non_english_ratio=0.20
        )
        
        is_english, stats = detector.detect(text, verbose=True)
        
        # Log detection results
        print(f"\n📊 Language Detection Results:")
        print(f"   English Ratio: {stats.get('english_ratio', 0):.1%}")
        print(f"   Non-English Ratio: {stats.get('non_english_ratio', 0):.1%}")
        print(f"   English chars: {stats.get('english_letters', 0)}")
        print(f"   Non-English chars: {stats.get('non_english_chars', 0)}")
        print(f"   Result: {'✅ ACCEPTED' if is_english else '❌ REJECTED'}\n")
        
        return is_english
        
    except Exception as e:
        print(f"❌ Error checking language for {file.filename}: {e}")
        # Fail-safe: accept the document if error occurs
        return True
    
def is_pdf_file(file):
    """
    Checks whether the uploaded file is a valid PDF.

    Args:
        file: Werkzeug FileStorage object (request.files['file'])

    Returns:
        bool: True if PDF, False otherwise
    """

    if not file:
        return False

    # 1. Check file extension
    filename = file.filename
    if not filename or not filename.lower().endswith(".pdf"):
        return False

    # 2. Check MIME type (extra safety)
    if file.mimetype != "application/pdf":
        return False

    return True

def is_invalid_file(file_path: str) -> bool:
    """
    INVALID if:
    - missing
    - zero-byte
    - corrupt
    - encrypted
    - PDF with:
        - no meaningful text AND
        - no images
    Vector-only PDFs are treated as EMPTY.
    """

    try:
        # 1️⃣ File existence
        if not os.path.exists(file_path):
            return True

        # 2️⃣ Zero-byte
        if os.path.getsize(file_path) == 0:
            return True

        # 3️⃣ Binary read test
        with open(file_path, "rb") as f:
            f.read(1)

        # 4️⃣ PDF validation
        if file_path.lower().endswith(".pdf"):
            reader = PdfReader(file_path)

            if reader.is_encrypted:
                return True

            if len(reader.pages) == 0:
                return True

            total_alpha_chars = 0
            image_found = False

            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # TEXT (real content)
                    text = page.extract_text()
                    if text:
                        cleaned = re.sub(r"[^A-Za-z]", "", text)
                        total_alpha_chars += len(cleaned)

                    # IMAGES (scanned PDFs)
                    if page.images:
                        image_found = True

            # ✅ Image-only scanned PDFs are VALID
            if image_found and total_alpha_chars == 0:
                return False

            # ❌ No text AND no images → EMPTY PDF (vector-only, blank, layout junk)
            if total_alpha_chars < 50:
                return True

    except Exception:
        return True

    return False