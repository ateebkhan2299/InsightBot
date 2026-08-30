import os
import sys
os.environ['TESTING'] = 'true'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from unittest.mock import patch, MagicMock
from app import create_app
from scraper.scraper import Scraper
from scraper.extractor import ArticleExtractor
from scheduler.scheduler import scrape_website_job, get_next_scrape_time
from database.repositories import normalize_url, compute_content_hash, source_repository, article_repository

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Sample Global News</title>
    <link>https://news.example.com</link>
    <description>Latest Global News Headlines</description>
    <item>
      <title>Global Market Surges Amid Technology Growth</title>
      <link>https://news.example.com/articles/global-market-surges-101</link>
      <guid>https://news.example.com/articles/global-market-surges-101</guid>
      <pubDate>Sun, 30 Aug 2026 12:00:00 GMT</pubDate>
      <description>Markets worldwide posted strong quarterly gains today.</description>
    </item>
    <item>
      <title>Renewable Energy Adoption Reaches New Record</title>
      <link>https://news.example.com/articles/renewable-energy-record-102</link>
      <guid>https://news.example.com/articles/renewable-energy-record-102</guid>
      <pubDate>Sun, 30 Aug 2026 13:00:00 GMT</pubDate>
      <description>Solar and wind power installations increased by 40 percent.</description>
    </item>
  </channel>
</rss>
"""

SAMPLE_ARTICLE_HTML = """<!DOCTYPE html>
<html>
<head><title>Renewable Energy Adoption Reaches New Record - Example News</title></head>
<body>
  <article>
    <h1>Renewable Energy Adoption Reaches New Record</h1>
    <div class="date">August 30, 2026</div>
    <div class="author">By Jane Doe</div>
    <p>Solar and wind power installations increased by forty percent over the past year across major global economies.</p>
    <p>Government initiatives and falling hardware prices have accelerated adoption in both domestic and industrial sectors.</p>
    <p>Experts forecast continuous acceleration in renewable capacity additions through the end of the decade.</p>
  </article>
</body>
</html>
"""

class TestSchedulerIncremental(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_rss_feed_detection_and_link_parsing(self):
        scraper = Scraper()
        self.assertTrue(scraper.is_feed_content(SAMPLE_RSS))
        links = scraper.parse_feed_links(SAMPLE_RSS, base_url="https://news.example.com")
        self.assertEqual(len(links), 2)
        self.assertIn("https://news.example.com/articles/global-market-surges-101", links)
        self.assertIn("https://news.example.com/articles/renewable-energy-record-102", links)

    def test_url_normalization_and_hash(self):
        url1 = "https://news.example.com/articles/renewable-energy-record-102/?utm_source=twitter&utm_medium=social"
        url2 = "https://news.example.com/articles/renewable-energy-record-102"
        self.assertEqual(normalize_url(url1), normalize_url(url2))

        hash1 = compute_content_hash("Test Title", "Body text content.", "example.com")
        hash2 = compute_content_hash("test title", "body text content.", "example.com")
        self.assertEqual(hash1, hash2)

    def test_incremental_scraping_duplicate_skipping(self):
        scraper = Scraper()
        extractor = ArticleExtractor()

        art = extractor.extract(SAMPLE_ARTICLE_HTML, source_url="https://news.example.com/articles/renewable-energy-record-102")
        self.assertEqual(art['title'], "Renewable Energy Adoption Reaches New Record")

        content_hash = compute_content_hash(art['title'], art['body'], 'news.example.com')
        mock_coll = MagicMock()
        mock_coll.find_one.return_value = {"_id": "123", "content_hash": content_hash, "version": 1}
        with patch('database.repositories.db_connection.get_collection', return_value=mock_coll):
            saved = article_repository.save_to_db(art)
            self.assertFalse(saved)
            self.assertEqual(art.get('ingestion_status'), 'duplicate')

    def test_unreachable_url_handling(self):
        website_doc = {
            "name": "Invalid Domain",
            "url": "http://this-is-an-invalid-nonexistent-domain-xyz-12345.org/rss",
            "active": True,
            "schedule": "daily"
        }
        try:
            scrape_website_job(website_doc)
            passed = True
        except Exception:
            passed = False
        self.assertTrue(passed, "scrape_website_job should catch all exceptions and not crash")


if __name__ == '__main__':
    unittest.main()
