import unittest
from bs4 import BeautifulSoup
from preprocessing.cleaner import HTMLCleaner
from preprocessing.language_utils import LanguageUtils

class TestPreprocessing(unittest.TestCase):
    def test_clean_html(self):
        raw_html = "<html><body><script>alert(1);</script><h1>Title</h1><style>body{color:red;}</style></body></html>"
        soup = HTMLCleaner.clean_html(raw_html)
        text = soup.get_text()
        self.assertNotIn("alert(1)", text)
        self.assertNotIn("color:red", text)
        self.assertIn("Title", text)

    def test_language_detection_arabic(self):
        text = "مرحبا بالعالم كيف حالك اليوم"
        self.assertEqual(LanguageUtils.detect_language(text), "Arabic")

    def test_language_detection_russian(self):
        text = "Привет мир как дела сегодня"
        self.assertEqual(LanguageUtils.detect_language(text), "Russian")

    def test_language_detection_english(self):
        text = "Hello world this is breaking news today"
        self.assertEqual(LanguageUtils.detect_language(text), "English")

if __name__ == '__main__':
    unittest.main()
