import re
from typing import Dict, Tuple

class EnglishLanguageDetector:
    """
    Robust English language detector using positive matching of English characters.
    Instead of blacklisting non-English scripts, we whitelist English characters.
    """
    
    def __init__(self, english_threshold: float = 0.80, max_non_english_ratio: float = 0.20):
        """
        Args:
            english_threshold: Minimum ratio of English content required (0-1)
            max_non_english_ratio: Maximum allowed ratio of non-English content (0-1)
        """
        self.english_threshold = english_threshold
        self.max_non_english_ratio = max_non_english_ratio
        
        # Define acceptable English character ranges (Unicode)
        self.english_ranges = [
            (0x0041, 0x005A),  # A-Z (uppercase)
            (0x0061, 0x007A),  # a-z (lowercase)
            (0x00C0, 0x00D6),  # Latin-1 Supplement uppercase (À-Ö)
            (0x00D8, 0x00F6),  # Latin-1 Supplement uppercase continued (Ø-ö)
            (0x00F8, 0x00FF),  # Latin-1 Supplement lowercase (ø-ÿ)
            (0x0100, 0x017F),  # Latin Extended-A (Ā-ſ)
            (0x0180, 0x024F),  # Latin Extended-B (ƀ-ɏ)
        ]
        
        # Common punctuation and symbols used in English
        self.english_punctuation = set(
            '.,;:!?\'""-–—()[]{}/@#$%^&*+=<>~`|\\…""''•·'
        )
    
    def _is_english_letter(self, char: str) -> bool:
        """Check if a character is an English/Latin letter."""
        code_point = ord(char)
        for start, end in self.english_ranges:
            if start <= code_point <= end:
                return True
        return False
    
    def _is_acceptable_char(self, char: str) -> bool:
        """Check if character is acceptable in English text."""
        return (
            self._is_english_letter(char) or
            char in self.english_punctuation or
            char.isspace() or
            char.isdigit()
        )
    
    def _count_character_types(self, text: str) -> Dict[str, int]:
        """Count different types of characters in the text."""
        counts = {
            'english_letters': 0,
            'non_english_chars': 0,
            'digits': 0,
            'punctuation': 0,
            'whitespace': 0,
        }
        
        for char in text:
            if char.isspace():
                counts['whitespace'] += 1
            elif char.isdigit():
                counts['digits'] += 1
            elif char in self.english_punctuation:
                counts['punctuation'] += 1
            elif self._is_english_letter(char):
                counts['english_letters'] += 1
            else:
                # Anything not recognized as English is non-English
                counts['non_english_chars'] += 1
        
        return counts
    
    def _clean_text_for_analysis(self, text: str) -> str:
        """Remove elements that shouldn't count toward language detection."""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        
        # Remove file paths (Windows and Unix style)
        text = re.sub(r'[A-Za-z]:\\(?:[^\\\s]+\\)*[^\\\s]*', '', text)
        text = re.sub(r'/(?:[^/\s]+/)+[^/\s]*', '', text)
        
        # Remove standalone numbers and dates
        text = re.sub(r'\b\d+([.,:/\-]\d+)*\b', '', text)
        
        # Remove common programming/technical syntax that might contain symbols
        text = re.sub(r'[{}\[\]<>]+', '', text)
        
        return text
    
    def detect(self, text: str, verbose: bool = False) -> Tuple[bool, Dict]:
        """
        Detect if text is predominantly English.
        
        Args:
            text: Text to analyze
            verbose: If True, return detailed statistics
            
        Returns:
            Tuple of (is_english: bool, stats: dict)
        """
        if not text or not text.strip():
            # Image-only or no extractable text → assume English
            return True, {
                'is_english': True,
                'assumed_english': True,
                'reason': 'No extractable text found (image-only document)',
                'english_ratio': 1.0,
                'non_english_ratio': 0.0,
                'total_meaningful_chars': 0
            }

        # Clean text for analysis
        cleaned_text = self._clean_text_for_analysis(text)

        # Count character types
        counts = self._count_character_types(cleaned_text)

        # Calculate meaningful characters
        meaningful_chars = (
            counts['english_letters'] +
            counts['non_english_chars']
        )

        if meaningful_chars == 0:
            # Image-only or symbol-only document → assume English
            return True, {
                'is_english': True,
                'assumed_english': True,
                'reason': 'No meaningful characters after cleaning (image-only document)',
                'english_ratio': 1.0,
                'non_english_ratio': 0.0,
                'total_meaningful_chars': 0
            }

        # Calculate ratios
        english_ratio = counts['english_letters'] / meaningful_chars
        non_english_ratio = counts['non_english_chars'] / meaningful_chars

        # Decision logic (UNCHANGED)
        is_english = (
            english_ratio >= self.english_threshold and
            non_english_ratio <= self.max_non_english_ratio
        )

        stats = {
            'is_english': is_english,
            'english_ratio': round(english_ratio, 3),
            'non_english_ratio': round(non_english_ratio, 3),
            'english_letters': counts['english_letters'],
            'non_english_chars': counts['non_english_chars'],
            'total_meaningful_chars': meaningful_chars,
            'threshold_used': self.english_threshold,
            'max_non_english_allowed': self.max_non_english_ratio,
            'meets_english_threshold': english_ratio >= self.english_threshold,
            'within_non_english_limit': non_english_ratio <= self.max_non_english_ratio
        }

        if verbose:
            stats.update({
                'digits': counts['digits'],
                'punctuation': counts['punctuation'],
                'whitespace': counts['whitespace'],
            })

        return is_english, stats


# Example usage
if __name__ == "__main__":
    # Allow up to 20% non-English content, require 80% English
    detector = EnglishLanguageDetector(english_threshold=0.80, max_non_english_ratio=0.20)
    
    # Test cases
    test_texts = [
        "This is a purely English document with no foreign characters.",
        "یہ اردو میں ہے but some English words in (brackets) and headings",
        "This is English with a few اردو words scattered around the text",
        "Complete English text with numbers 123 and punctuation!",
        "مکمل اردو متن بغیر کسی انگریزی کے",
        "Mixed content: یہ document has both languages equally distributed",
        "Résumé with café and naïve - English with accents",
        "这是中文 with some English words",
        "100% English with café, résumé, and other borrowed words!",
    ]
    
    print("English Language Detection Results (Positive Matching):\n" + "="*70)
    
    for i, text in enumerate(test_texts, 1):
        is_english, stats = detector.detect(text, verbose=True)
        
        # Safely truncate text for display
        display_text = text[:50] + "..." if len(text) > 50 else text
        
        print(f"\nTest {i}:")
        print(f"Text: {display_text}")
        print(f"✓ Is English: {is_english}")
        print(f"  English Ratio: {stats['english_ratio']:.1%} (threshold: {stats['threshold_used']:.1%})")
        print(f"  Non-English Ratio: {stats['non_english_ratio']:.1%} (max allowed: {stats['max_non_english_allowed']:.1%})")
        print(f"  English chars: {stats['english_letters']} | Non-English chars: {stats['non_english_chars']}")
        print("-" * 70)