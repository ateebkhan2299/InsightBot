"""
InsightBot - Bulk Data Population Script
=========================================
Scrapes articles from all 40 training URLs and saves them to MongoDB.
Run this to populate the database for demo purposes.

Usage:
    python bulk_scrape.py
"""
import os
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

from database.mongodb import db_connection
from database.repositories import article_repository
from scraper.scraper import Scraper
from scraper.extractor import ArticleExtractor

# ── Real article URLs (actual articles, not homepages) ──────────────────
ARTICLE_URLS = [
    # English - BBC
    "https://www.bbc.com/news/world",
    "https://www.bbc.com/news/science-environment",
    "https://www.bbc.com/news/technology",
    # English - AP News
    "https://apnews.com/world-news",
    "https://apnews.com/hub/science",
    "https://apnews.com/hub/technology",
    # English - NPR
    "https://www.npr.org/sections/world/",
    "https://www.npr.org/sections/technology/",
    # English - Ars Technica
    "https://arstechnica.com",
    "https://arstechnica.com/science/",
    # English - Time
    "https://time.com/section/world/",
    "https://time.com/section/tech/",
    # English - The Atlantic
    "https://www.theatlantic.com",
    # English - CNN
    "https://edition.cnn.com/world",
    # English - CBS
    "https://www.cbsnews.com/world/",
    # English - NBC
    "https://www.nbcnews.com/world",
    # English - HuffPost
    "https://www.huffpost.com/news/world-news",
    # English - USA Today
    "https://www.usatoday.com/news/world/",
    # English - Independent
    "https://www.independent.co.uk/news/world",
    # English - TechCrunch
    "https://www.techcrunch.com",

    # Arabic - Al Jazeera
    "https://www.aljazeera.net/news/",
    "https://www.aljazeera.net/economy/",
    # Arabic - RT Arabic
    "https://arabic.rt.com/",
    "https://arabic.rt.com/world/",
    # Arabic - BBC Arabic
    "https://www.bbc.com/arabic/world",
    # Arabic - Sky News Arabia
    "https://www.skynewsarabia.com/world",
    "https://www.skynewsarabia.com/technology",
    # Arabic - Al Bawaba
    "https://www.albawabhnews.com/",
    # Arabic - Al Hurra
    "https://www.alhurra.com/",
    # Arabic - Anadolu Agency
    "https://www.aa.com.tr/ar/",

    # Russian - RT
    "https://www.rt.com/russia/",
    "https://www.rt.com/news/",
    # Russian - RIA Novosti
    "https://ria.ru/",
    # Russian - Interfax
    "https://www.interfax.ru/",
    # Russian - Meduza
    "https://meduza.io/",
    # Russian - Izvestia
    "https://iz.ru/",
    # Russian - 1TV
    "https://www.1tv.ru/news",
]


def run_bulk_scrape():
    print("=" * 60)
    print("  InsightBot - Bulk Database Population")
    print(f"  Target: {len(ARTICLE_URLS)} URLs across EN/AR/RU")
    print("=" * 60)

    # Connect to MongoDB
    if not db_connection.connect():
        print("ERROR: Cannot connect to MongoDB. Is it running?")
        return

    before_count = article_repository.collection.count_documents({})
    print(f"\n  Articles in DB before: {before_count}")
    print()

    scraper   = Scraper(timeout=12, retries=2)
    extractor = ArticleExtractor()

    saved = 0
    failed = 0
    skipped = 0

    for i, url in enumerate(ARTICLE_URLS, 1):
        print(f"[{i:02d}/{len(ARTICLE_URLS)}] {url[:65]}", end=" ... ")

        try:
            html = scraper.fetch_html(url)
            if not html or len(html) < 500:
                print("FAILED (no content)")
                failed += 1
                continue

            article = extractor.extract(html, source_url=url)

            # Skip if extraction produced nothing useful
            if not article.get('title') or article['title'] == 'Unknown Title':
                print("SKIPPED (no title extracted)")
                skipped += 1
                continue

            if not article.get('body') or len(article['body']) < 50:
                print("SKIPPED (body too short)")
                skipped += 1
                continue

            # Save to MongoDB (upsert — no duplicates)
            ok = article_repository.save_to_db(article)
            if ok:
                lang = article.get('language', '?')
                words = len(article.get('body', '').split())
                print(f"SAVED [{lang}] ({words} words)")
                saved += 1
            else:
                print("DB ERROR")
                failed += 1

        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1

    after_count = article_repository.collection.count_documents({})

    print()
    print("=" * 60)
    print("  BULK SCRAPE COMPLETE")
    print(f"  Saved    : {saved}")
    print(f"  Skipped  : {skipped} (anti-bot / JS-heavy sites)")
    print(f"  Failed   : {failed}")
    print(f"  DB Before: {before_count} articles")
    print(f"  DB After : {after_count} articles")
    print(f"  New Added: {after_count - before_count} articles")
    print("=" * 60)

    # Also export fresh CSVs for Tableau
    print("\n  Exporting fresh Tableau CSVs...")
    try:
        from scraper.export_csv import export_for_tableau
        export_for_tableau()
    except Exception as e:
        print(f"  CSV export error: {e}")


if __name__ == "__main__":
    run_bulk_scrape()
