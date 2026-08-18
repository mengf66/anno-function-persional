"""Tests for text_word_counter function."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from main import main


class TextWordCounterTest(unittest.TestCase):
    def test_chinese_only(self):
        result = main("你好世界")
        self.assertEqual(
            result,
            {"chinese_chars": 4, "english_words": 0, "total_chars": 4},
        )

    def test_english_only(self):
        result = main("Hello World")
        self.assertEqual(
            result,
            {"chinese_chars": 0, "english_words": 2, "total_chars": 10},
        )

    def test_mixed(self):
        result = main("Hello 你好世界")
        self.assertEqual(
            result,
            {"chinese_chars": 4, "english_words": 1, "total_chars": 9},
        )

    def test_empty(self):
        result = main("")
        self.assertEqual(
            result,
            {"chinese_chars": 0, "english_words": 0, "total_chars": 0},
        )

    def test_with_numbers_and_punctuation(self):
        result = main("测试123！")
        self.assertEqual(
            result,
            {"chinese_chars": 2, "english_words": 0, "total_chars": 6},
        )
