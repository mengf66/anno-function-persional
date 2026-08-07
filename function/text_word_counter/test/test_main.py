"""Tests for text_word_counter function."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from main import main


def test_chinese_only():
    result = main("你好世界")
    assert result == {"chinese_chars": 4, "english_words": 0, "total_chars": 4}


def test_english_only():
    result = main("Hello World")
    assert result == {"chinese_chars": 0, "english_words": 2, "total_chars": 10}


def test_mixed():
    result = main("Hello 你好世界")
    assert result == {"chinese_chars": 4, "english_words": 1, "total_chars": 9}


def test_empty():
    result = main("")
    assert result == {"chinese_chars": 0, "english_words": 0, "total_chars": 0}


def test_with_numbers_and_punctuation():
    result = main("测试123！")
    assert result == {"chinese_chars": 2, "english_words": 0, "total_chars": 6}
