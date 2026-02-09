"""
table_extractor.py
------------------
Extracts semantically meaningful tables from PDFs and converts them to text.
Ignores purely numeric or non-informative tables.
"""

import pdfplumber
import pandas as pd
import re
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


# ---------------------------
# Utility checks
# ---------------------------

def is_numeric(value):
    try:
        value = str(value).strip()
        return bool(re.fullmatch(r"[-+]?\d*\.?\d+", value))
    except:
        return False


def numeric_ratio(df: pd.DataFrame) -> float:
    total_cells = df.size
    if total_cells == 0:
        return 1.0

    numeric_cells = 0
    for col in df.columns:
        for val in df[col]:
            if is_numeric(val):
                numeric_cells += 1

    return numeric_cells / total_cells


def has_textual_headers(df: pd.DataFrame) -> bool:
    for col in df.columns:
        col = str(col).strip()
        if not is_numeric(col) and len(col) > 1:
            return True
    return False


def semantic_richness(df: pd.DataFrame) -> bool:
    text_lengths = []
    for col in df.columns:
        for val in df[col]:
            val = str(val).strip()
            if not is_numeric(val):
                text_lengths.append(len(val))

    if not text_lengths:
        return False

    avg_len = sum(text_lengths) / len(text_lengths)
    return avg_len > 5  # threshold for meaningful text


# ---------------------------
# Table validation
# ---------------------------

def is_meaningful_table(df: pd.DataFrame, numeric_threshold: float = 0.85) -> bool:
    # Basic shape check
    if df.shape[0] < 2 or df.shape[1] < 1:
        return False

    # Empty table check
    if df.empty or df.isnull().all().all():
        return False

    # Header check - allow tables without textual headers if they have meaningful content
    has_headers = has_textual_headers(df)

    # Numeric dominance check - relaxed threshold for tables with headers
    numeric_ratio_val = numeric_ratio(df)
    if numeric_ratio_val > numeric_threshold and not has_headers:
        return False

    # Semantic richness check - only enforce if we have textual headers
    if has_headers and not semantic_richness(df):
        return False
   
    return True


# ---------------------------
# Table → Text conversion
# ---------------------------

def table_to_text(df: pd.DataFrame) -> str:
    """Convert table to structured text with headers and content on the same line."""
    headers = [str(h).strip() for h in df.columns]
    rows_text = []

    for _, row in df.iterrows():
        # Add all header-content pairs for this row, each on a new line
        for h, cell in zip(headers, row):
            cell = str(cell).strip()
            # Replace newlines and extra whitespace with a single space
            cell = " ".join(cell.split())
            # Include non-empty cells (both text and numeric)
            if cell and cell.lower() not in ['nan', 'none', '']:
                rows_text.append(f"{h}: {cell}")

    return "\n".join(rows_text) if rows_text else ""


# ---------------------------
# Main extraction logic
# ---------------------------

def extract_tables_pdfplumber(pdf_path: str, numeric_threshold: float = 0.85):
    extracted_text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if not tables:
                    continue
                    
                for table_idx, table in enumerate(tables):
                    try:
                        if not table or len(table) < 2:
                            continue
                        
                        df = pd.DataFrame(table[1:], columns=table[0])
                        
                        if is_meaningful_table(df, numeric_threshold):
                            text = table_to_text(df)
                            if text:  # Only add non-empty results
                                extracted_text.append(text)
                    except Exception as e:
                        logger.warning(f"Error processing pdfplumber table at page {page_idx}, table {table_idx}: {e}")
                        continue
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed for {pdf_path}: {e}")

    return extracted_text


# ---------------------------
# Public API (USE THIS)
# ---------------------------

def extract_meaningful_tables(pdf_path: str, numeric_threshold: float = 0.85, skip_tables: bool = False) -> str:
    """
    Extracts meaningful tables from a PDF and returns them as clean text.
    
    Args:
        pdf_path: Path to the PDF file
        numeric_threshold: Maximum ratio of numeric cells (0-1). Default 0.85 allows 
                          statistical/financial tables. Lower values are stricter.
        skip_tables: If True, completely skip table extraction and return empty string
    
    Returns:
        Combined text from all meaningful tables separated by double newlines.
        Returns empty string if skip_tables is True.
    """
    if skip_tables:
        return ""
    
    all_text = []
    # Use pdfplumber for table extraction
    plumber_text = extract_tables_pdfplumber(pdf_path, numeric_threshold)
    all_text.extend(plumber_text)
    return "\n\n".join(all_text)

if __name__ == "__main__":
    # Example usage
    pdf_file = r"C:\BLS\EvalAI8\Uploads\K_Asad_Thesis.pdf"
    extracted = extract_meaningful_tables(pdf_file)
    print("Extracted Tables Text:\n", extracted)