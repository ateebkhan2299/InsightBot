import os
import sys
import csv
import re
from collections import Counter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.repositories import article_repository
from database.mongodb import db_connection
from config.config import config


def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'[^\w\s]', '', text.lower())


def compute_top_keywords(articles: list, limit: int = 20) -> list:
    stopwords = {
        "the", "and", "to", "of", "a", "in", "for", "is", "on", "that", "by",
        "this", "with", "i", "you", "it", "not", "or", "be", "are", "from",
        "at", "as", "your", "all", "have", "new", "more", "an", "was", "we",
        "will", "home", "us", "about", "what", "when", "how", "why", "but",
        "they", "he", "she", "has", "their", "our", "its"
    }

    word_counts = Counter()
    for article in articles:
        content = f"{article.get('title', '')} {article.get('body', '')}"
        words = clean_text(content).split()
        for word in words:
            if len(word) > 3 and not word.isnumeric() and word not in stopwords:
                word_counts[word] += 1

    return word_counts.most_common(limit)


def export_for_tableau():
    db_connection.connect()
    coll = article_repository.collection
    if coll is None:
        return

    articles = list(coll.find({}, {"_id": 0}))
    if not articles:
        return

    os.makedirs(config.OUTPUT_DATA_DIR, exist_ok=True)

    tableau_file = os.path.join(config.OUTPUT_DATA_DIR, "tableau_export.csv")
    keys = ["domain", "language", "published_date", "title"]

    try:
        with open(tableau_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for article in articles:
                url = article.get('source_url', '')
                domain = url.split('/')[2] if '//' in url else url.split('/')[0]
                writer.writerow({
                    "domain": domain,
                    "language": article.get("language", "Unknown"),
                    "published_date": article.get("publication_date", "Unknown"),
                    "title": article.get("title", "")
                })
    except Exception as exc:
        print(f"Error writing tableau_export.csv: {exc}")

    keyword_file = os.path.join(config.OUTPUT_DATA_DIR, "keyword_frequency.csv")
    top_keywords = compute_top_keywords(articles, limit=20)

    try:
        with open(keyword_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["keyword", "frequency"])
            for word, freq in top_keywords:
                writer.writerow([word, freq])
    except Exception as exc:
        print(f"Error writing keyword_frequency.csv: {exc}")


if __name__ == "__main__":
    export_for_tableau()
