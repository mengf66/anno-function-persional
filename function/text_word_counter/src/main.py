"""Text word counter — counts Chinese characters, English words, and total characters."""

import re
import unicodedata


def _is_chinese(char: str) -> bool:
    """Check if a character is a CJK unified ideograph."""
    try:
        return "CJK UNIFIED IDEOGRAPH" in unicodedata.name(char)
    except ValueError:
        return False


def count_text(text: str) -> dict:
    """Count Chinese characters, English words, and total non-whitespace characters."""
    chinese_chars = sum(1 for ch in text if _is_chinese(ch))

    # Extract English words (consecutive ASCII letters)
    english_words = len(re.findall(r"[a-zA-Z]+", text))

    # Total characters excluding whitespace
    total_chars = sum(1 for ch in text if not ch.isspace())

    return {
        "chinese_chars": chinese_chars,
        "english_words": english_words,
        "total_chars": total_chars,
    }


def main(text: str) -> dict:
    """Run the Function with parameters supplied by anno-function-runner."""
    return count_text(text)
