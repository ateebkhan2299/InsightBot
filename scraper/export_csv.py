import os
import sys
import csv
import re
from collections import Counter

# Add parent directory to path so we can import from database and config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.repositories import article_repository
from config.config import config

def clean_text(text):
    """Simple tokenizer and basic cleaner."""
    if not text:
        return ""
    # Remove punctuation and lowercase
    text = re.sub(r'[^\w\s]', '', text.lower())
    return text

def compute_top_keywords(articles, limit=20):
    """Computes top keywords across all articles using basic stopword removal."""
    # Basic stopwords (English only for this simple implementation)
    stopwords = set([
        "the", "and", "to", "of", "a", "in", "for", "is", "on", "that", "by", 
        "this", "with", "i", "you", "it", "not", "or", "be", "are", "from", 
        "at", "as", "your", "all", "have", "new", "more", "an", "was", "we",
        "will", "home", "us", "about", "what", "when", "how", "why", "but",
        "they", "he", "she", "has", "their", "our", "its"
    ])
    
    word_counts = Counter()
    
    for article in articles:
        # Combine title and body
        content = f"{article.get('title', '')} {article.get('body', '')}"
        words = clean_text(content).split()
        
        for word in words:
            # Filter out short words, numbers, and stopwords
            if len(word) > 3 and not word.isnumeric() and word not in stopwords:
                word_counts[word] += 1
                
    return word_counts.most_common(limit)

def export_for_tableau():
    """Exports articles and keyword frequencies to CSV for Tableau."""
    print("Connecting to MongoDB...")
    # Explicitly connect when running as a standalone script
    from database.mongodb import db_connection
    if not db_connection.connect():
        print("Error: Could not connect to MongoDB.")
        return
        
    # Get all articles (no limit for export)
    # Using the underlying collection to bypass the 100 limit in the repository's get_all
    coll = article_repository.collection
    if coll is None:
        print("Error: Could not connect to MongoDB.")
        return
        
    articles = list(coll.find({}, {"_id": 0}))
    print(f"Retrieved {len(articles)} articles from database.")
    
    if not articles:
        print("No articles found to export.")
        return

    # Ensure output directory exists
    os.makedirs(config.OUTPUT_DATA_DIR, exist_ok=True)
    
    # 1. Export Flat Articles CSV
    tableau_file = os.path.join(config.OUTPUT_DATA_DIR, "tableau_export.csv")
    keys = ["domain", "language", "published_date", "title"]
    
    try:
        with open(tableau_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for article in articles:
                # Extract domain from source_url
                url = article.get('source_url', '')
                domain = url.split('/')[2] if '//' in url else url.split('/')[0]
                
                writer.writerow({
                    "domain": domain,
                    "language": article.get("language", "Unknown"),
                    "published_date": article.get("publication_date", "Unknown"),
                    "title": article.get("title", "")
                })
        print(f"Successfully exported {len(articles)} records to {tableau_file}")
    except Exception as e:
        print(f"Error writing tableau_export.csv: {e}")

    # 2. Export Keyword Frequencies CSV
    keyword_file = os.path.join(config.OUTPUT_DATA_DIR, "keyword_frequency.csv")
    top_keywords = compute_top_keywords(articles, limit=20)
    
    try:
        with open(keyword_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["keyword", "frequency"])
            for word, freq in top_keywords:
                writer.writerow([word, freq])
        print(f"Successfully exported Top {len(top_keywords)} keywords to {keyword_file}")
        
        print("\n--- TOP 20 KEYWORDS ---")
        for i, (word, freq) in enumerate(top_keywords, 1):
            print(f"{i}. {word} ({freq} occurrences)")
            
    except Exception as e:
        print(f"Error writing keyword_frequency.csv: {e}")

if __name__ == "__main__":
    export_for_tableau()
