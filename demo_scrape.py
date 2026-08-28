import os
from dotenv import load_dotenv

load_dotenv()

from scraper.scraper import Scraper
from scraper.extractor import ArticleExtractor
from database.repositories import article_repository, log_repository
from database.mongodb import db_connection


def run_demo():
    db_connection.connect()
    scraper = Scraper()
    extractor = ArticleExtractor()

    urls = [
        "https://www.bbc.com/news/articles/cx2y3q9z1y9o",
        "https://www.aljazeera.net/news/2023/10/30/un-warns-of-gaza-crisis",
        "https://lenta.ru/news/2023/10/30/russia_news/"
    ]

    extracted_articles = []
    for url in urls:
        print(f"Scraping {url}...")
        html = scraper.fetch_html(url)
        if html:
            article = extractor.extract(html, source_url=url)
            if article.get('title') and article.get('body'):
                print(f"  Extracted: {article['title'][:40]}...")
                if article_repository.save_to_db(article):
                    extracted_articles.append(article)
                    log_repository.log_event("SUCCESS", f"Demo extracted {url}", url)
            else:
                print("  No valid article content found.")
        else:
            print("  Failed to fetch HTML.")

    if extracted_articles:
        all_articles = article_repository.get_all(limit=0)
        article_repository.save_to_json(all_articles)
        article_repository.save_to_csv(all_articles)

    print("Demo scraping completed.")


if __name__ == "__main__":
    run_demo()
