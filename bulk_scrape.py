import os
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database.mongodb import db_connection
from database.repositories import article_repository
from scraper.scraper import Scraper
from scraper.extractor import ArticleExtractor
from scraper.export_csv import export_for_tableau

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

ARTICLE_URLS = [
    "https://www.bbc.com/news/world",
    "https://www.bbc.com/news/science-environment",
    "https://www.bbc.com/news/technology",
    "https://apnews.com/world-news",
    "https://apnews.com/hub/science",
    "https://apnews.com/hub/technology",
    "https://www.npr.org/sections/world/",
    "https://www.npr.org/sections/technology/",
    "https://arstechnica.com",
    "https://arstechnica.com/science/",
    "https://time.com/section/world/",
    "https://time.com/section/tech/",
    "https://www.theatlantic.com",
    "https://edition.cnn.com/world",
    "https://www.cbsnews.com/world/",
    "https://www.nbcnews.com/world",
    "https://www.huffpost.com/news/world-news",
    "https://www.usatoday.com/news/world/",
    "https://www.independent.co.uk/news/world",
    "https://www.techcrunch.com",
    "https://www.aljazeera.net/news/",
    "https://www.aljazeera.net/economy/",
    "https://arabic.rt.com/",
    "https://arabic.rt.com/world/",
    "https://www.bbc.com/arabic/world",
    "https://www.skynewsarabia.com/world",
    "https://www.skynewsarabia.com/technology",
    "https://www.albawabhnews.com/",
    "https://www.alhurra.com/",
    "https://www.aa.com.tr/ar/",
    "https://www.rt.com/russia/",
    "https://www.rt.com/news/",
    "https://ria.ru/",
    "https://www.interfax.ru/",
    "https://meduza.io/",
    "https://iz.ru/",
    "https://www.1tv.ru/news",
]


def run_bulk_scrape():
    if not db_connection.connect():
        print("Error: Unable to connect to MongoDB.")
        return

    scraper = Scraper(timeout=12, retries=2)
    extractor = ArticleExtractor()

    saved_count = 0
    for i, url in enumerate(ARTICLE_URLS, 1):
        print(f"[{i:02d}/{len(ARTICLE_URLS)}] {url[:60]} ...", end=" ")
        try:
            html = scraper.fetch_html(url)
            if not html or len(html) < 500:
                print("FAILED")
                continue

            article = extractor.extract(html, source_url=url)
            if not article.get('title') or article['title'] == 'Unknown Title':
                print("SKIPPED (no title)")
                continue

            if not article.get('body') or len(article['body']) < 50:
                print("SKIPPED (body too short)")
                continue

            if article_repository.save_to_db(article):
                print("SAVED")
                saved_count += 1
            else:
                print("EXISTS/SKIPPED")

        except Exception as exc:
            print(f"ERROR: {exc}")

    print(f"\nBulk scraping complete. Saved {saved_count} articles.")
    try:
        export_for_tableau()
    except Exception as exc:
        print(f"Export error: {exc}")


if __name__ == "__main__":
    run_bulk_scrape()
