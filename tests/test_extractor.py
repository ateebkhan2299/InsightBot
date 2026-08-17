import unittest
from scraper.extractor import ArticleExtractor
from scraper.pattern_mining import PatternMiner

class TestExtractor(unittest.TestCase):
    def test_extractor_initialization(self):
        extractor = ArticleExtractor()
        self.assertIsNotNone(extractor)
        self.assertIsInstance(extractor.miner, PatternMiner)

    def test_extractor_logic(self):
        html = "<html><body><h1>Test Title</h1><div class='content'><p>Test body paragraph that has enough length to qualify as a real sentence.</p></div></body></html>"
        extractor = ArticleExtractor()
        extractor.miner.rules = {
            "title_selectors": ["h1"],
            "body_selectors": ["div.content"],
            "date_selectors": []
        }
        result = extractor.extract(html, "http://test.com")
        self.assertEqual(result['title'], 'Test Title')
        self.assertIn('Test body paragraph', result['body'])
        self.assertEqual(result['source_url'], 'http://test.com')

if __name__ == '__main__':
    unittest.main()
