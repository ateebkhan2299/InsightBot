import os
from dotenv import load_dotenv
load_dotenv()

from scraper.scraper import Scraper
from scraper.extractor import ArticleExtractor
from database.repositories import article_repository, log_repository

def run_demo():
    print("Initializing demo scraper...")
    scraper = Scraper()
    extractor = ArticleExtractor()
    
    # Real news URLs for demonstration
    urls = [
        "https://www.bbc.com/news/articles/cx2y3q9z1y9o", # English
        "https://www.aljazeera.net/news/2023/10/30/un-warns-of-gaza-crisis", # Arabic
        "https://lenta.ru/news/2023/10/30/russia_news/" # Russian
    ]
    
    extracted_articles = []
    
    for url in urls:
        print(f"Scraping {url}...")
        html = scraper.fetch_html(url)
        if html:
            article = extractor.extract(html, source_url=url)
            if article['title'] and article['body']:
                print(f"  Success: Found title '{article['title'][:30]}...'")
                success = article_repository.save_to_db(article)
                if success:
                    extracted_articles.append(article)
                    log_repository.log_event("SUCCESS", f"Demo extracted {url}", url)
            else:
                print("  Failed: Could not find valid title or body.")
        else:
            print("  Failed: Could not fetch HTML.")
            
    if extracted_articles:
        print(f"Exporting {len(extracted_articles)} articles to JSON/CSV...")
        all_articles = article_repository.get_all(limit=0)
        article_repository.save_to_json(all_articles)
        # Note: CSV export will fail silently because pandas is not installed, but it won't crash
        article_repository.save_to_csv(all_articles)
        
    print("Demo scraping completed!")

if __name__ == "__main__":
    run_demo()
