import os
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scraper.scraper import Scraper
from scraper.pattern_mining import PatternMiner

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_training_urls(filepath: str) -> list:
    if not os.path.exists(filepath):
        logger.error(f"Training URLs file not found: {filepath}")
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]


def run_training():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    training_file = os.path.join(project_root, 'data', 'training_urls.txt')
    rules_file = os.path.join(project_root, 'models', 'extraction_rules.json')

    urls = load_training_urls(training_file)
    if not urls:
        print("No training URLs found.")
        return

    print(f"Loaded {len(urls)} training URLs.")
    scraper = Scraper(timeout=12, retries=2)
    html_corpus = []

    for i, url in enumerate(urls, 1):
        print(f"[{i:02d}/{len(urls)}] Fetching: {url} ...", end=" ")
        html = scraper.fetch_html(url)
        if html and len(html) > 500:
            html_corpus.append(html)
            print(f"OK ({len(html)//1000} KB)")
        else:
            print("FAILED")

    if not html_corpus:
        print("No HTML pages retrieved for pattern mining.")
        return

    print(f"Mining patterns from {len(html_corpus)} pages...")
    miner = PatternMiner(rules_file_path=rules_file)
    miner.mine_patterns(html_corpus)
    miner.save_rules()
    print(f"Pattern rules saved to {rules_file}")


if __name__ == "__main__":
    run_training()
