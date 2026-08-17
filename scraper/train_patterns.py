"""
InsightBot - Pattern Mining Training Script
===========================================
SRS Requirement: "Use 40 websites to train DOM pattern matching"

This script reads all 40 training URLs from data/training_urls.txt,
fetches their real HTML, analyzes the DOM structure, and mines
common structural patterns (title selectors, body selectors, date selectors).

The mined rules are saved to models/extraction_rules.json and are
automatically used by the ArticleExtractor during runtime.

Run this script BEFORE running the main application to ensure
patterns are mined from real training data.

Usage:
    python scraper/train_patterns.py
"""

import os
import sys
import json
import logging

# Add parent directory to path so we can import project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scraper.scraper import Scraper
from scraper.pattern_mining import PatternMiner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_training_urls(filepath: str) -> list:
    """Load training URLs from file, skipping comments and blank lines."""
    urls = []
    if not os.path.exists(filepath):
        logger.error(f"Training URLs file not found: {filepath}")
        return urls
        
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip comments (lines starting with #) and blank lines
            if line and not line.startswith('#'):
                urls.append(line)
                
    return urls


def run_training():
    """
    Main training function.
    Phase 1: Fetch HTML from all 40 training websites.
    Phase 2: Run PatternMiner.mine_patterns() on collected HTML.
    Phase 3: Save learned rules to models/extraction_rules.json.
    """
    print("=" * 65)
    print("   InsightBot — DOM Pattern Mining Training Phase")
    print("   SRS: Training on 40 multilingual news websites")
    print("=" * 65)
    
    # Resolve paths relative to project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    training_file = os.path.join(project_root, 'data', 'training_urls.txt')
    rules_file    = os.path.join(project_root, 'models', 'extraction_rules.json')
    
    # Step 1: Load training URLs
    urls = load_training_urls(training_file)
    if not urls:
        print("No training URLs found. Aborting.")
        return
    
    print(f"\n[Step 1] Loaded {len(urls)} training URLs from {training_file}")
    
    # Step 2: Fetch HTML from each training URL
    scraper = Scraper(timeout=12, retries=2)
    html_corpus = []
    success_count = 0
    fail_count = 0
    
    print(f"\n[Step 2] Fetching HTML from {len(urls)} training websites...\n")
    
    for i, url in enumerate(urls, 1):
        print(f"  [{i:02d}/{len(urls)}] Fetching: {url}", end=" ... ")
        html = scraper.fetch_html(url)
        
        if html and len(html) > 500:  # At least 500 chars = real page
            html_corpus.append(html)
            success_count += 1
            print(f"OK ({len(html)//1000}KB)")
        else:
            fail_count += 1
            print("FAILED (skipped)")
    
    print(f"\n  Fetch Summary: {success_count} succeeded, {fail_count} failed")
    
    if success_count == 0:
        print("\nNo HTML fetched. Cannot mine patterns. Check internet connection.")
        return
    
    # Step 3: Run Pattern Mining on all collected HTML
    print(f"\n[Step 3] Mining structural patterns from {success_count} pages...")
    
    miner = PatternMiner(rules_file_path=rules_file)
    learned_rules = miner.mine_patterns(html_corpus)
    
    print(f"\n  Mined Rules Summary:")
    print(f"  Title Selectors : {learned_rules.get('title_selectors', [])}")
    print(f"  Body  Selectors : {learned_rules.get('body_selectors', [])}")
    print(f"  Date  Selectors : {learned_rules.get('date_selectors', [])}")
    
    # Step 4: Save rules
    os.makedirs(os.path.dirname(rules_file), exist_ok=True)
    miner.save_rules()
    
    print(f"\n[Step 4] Rules saved to: {rules_file}")
    print("\n" + "=" * 65)
    print(f"   TRAINING COMPLETE")
    print(f"   Pages trained on : {success_count}/{len(urls)}")
    print(f"   Rules file       : {rules_file}")
    print(f"   The extractor will now use these mined patterns.")
    print("=" * 65)


if __name__ == "__main__":
    run_training()
