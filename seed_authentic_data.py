import os
from dotenv import load_dotenv
load_dotenv()

from scraper.scraper import Scraper
from scraper.extractor import ArticleExtractor
from database.repositories import article_repository, source_repository

def run_seed():
    print("Initializing authentic data seeder...")
    scraper = Scraper()
    extractor = ArticleExtractor()
    
    # 40 Training URLs (English, Arabic, Russian)
    with open('data/training_urls.txt', 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
        
    # We also add some real ones to ensure valid data is in DB for demo
    real_urls = [
        "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "https://en.wikipedia.org/wiki/Space_exploration",
        "https://en.wikipedia.org/wiki/Renewable_energy",
        "https://ar.wikipedia.org/wiki/%D8%A7%D9%84%D8%B0%D9%83%D8%A7%D8%A1_%D8%A7%D9%84%D8%A7%D8%B5%D8%B7%D9%86%D8%A7%D8%B9%D9%8A",
        "https://ar.wikipedia.org/wiki/%D8%A7%D8%B3%D8%AA%D9%83%D8%B4%D8%A7%D9%81_%D8%A7%D9%84%D9%81%D8%B6%D8%A7%D8%A1",
        "https://ru.wikipedia.org/wiki/%D0%98%D1%81%D0%BA%D1%83%D1%81%D1%81%D1%82%D0%B2%D0%B5%D0%BD%D0%BD%D1%8B%D0%B9_%D0%B8%D0%BD%D1%82%D0%B5%D0%BB%D0%BB%D0%B5%D0%BA%D1%82",
        "https://ru.wikipedia.org/wiki/%D0%98%D1%81%D1%81%D0%BB%D0%B5%D0%B4%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5_%D0%BA%D0%BE%D1%81%D0%BC%D0%BE%D1%81%D0%B0"
    ]
    
    urls = real_urls + urls
    
    extracted_articles = []
    
    for url in urls[:40]: # strictly 40
        print(f"Adding source to DB: {url}")
        source_repository.add_source(url)
        
        # We won't scrape all 40 right now to save time, the crawler will do it.
        # But we'll scrape the real ones for the dashboard
        if url in real_urls:
            print(f"Scraping live data from {url}...")
            html = scraper.fetch_html(url)
            if html:
                article = extractor.extract(html, source_url=url)
                if article['title'] and article['body']:
                    success = article_repository.save_to_db(article)
                    if success:
                        extracted_articles.append(article)
                else:
                    print("  Failed: Could not find valid title or body.")
            else:
                print("  Failed: Could not fetch HTML.")
            
    print(f"Seeded {len(extracted_articles)} professional, authentic articles into the database and loaded 40 training sources!")

if __name__ == "__main__":
    run_seed()
