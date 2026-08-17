import os
import sys
import json
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Force UTF-8 output to handle Arabic/Russian characters on Windows
sys.stdout.reconfigure(encoding='utf-8')

from scraper.scraper import Scraper
from scraper.extractor import ArticleExtractor

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(message)s')

def evaluate_accuracy():
    print("=" * 60)
    print("   InsightBot - Extraction Accuracy Evaluation")
    print("   Testing generalization on 10 UNSEEN websites")
    print("=" * 60)
    
    gt_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'testing_ground_truth.json')
    gt_file = os.path.abspath(gt_file)
    
    if not os.path.exists(gt_file):
        print(f"Error: {gt_file} not found.")
        return
        
    with open(gt_file, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)
        
    scraper = Scraper(timeout=15, retries=2)
    extractor = ArticleExtractor()
    
    total_tests = len(ground_truth)
    if total_tests == 0:
        print("No testing data available.")
        return
        
    title_pass = 0
    body_pass = 0
    fetch_failures = 0
    
    print(f"\nLoaded {total_tests} unseen testing websites.\n")
    
    for i, item in enumerate(ground_truth, 1):
        url = item['url']
        expected_lang = item.get('language', 'Unknown')
        min_words = item.get('expected_body_min_words', 20)
        title_hint = item.get('expected_title_contains', '')

        print(f"[{i}/{total_tests}] Testing: {url}")
        
        # ✅ REAL HTTP fetch — no mocking
        html = scraper.fetch_html(url)
        
        if not html:
            print(f"  [FETCH FAILED] could not retrieve page\n")
            fetch_failures += 1
            continue
        
        # Run pattern-based extraction
        article = extractor.extract(html, source_url=url)
        
        title = article.get('title', '')
        body = article.get('body', '')
        body_word_count = len(body.split())
        
        # Evaluate Title: non-empty and contains a meaningful string
        title_ok = len(title.strip()) > 5
        if title_ok:
            title_pass += 1
        
        # Evaluate Body: has enough words
        body_ok = body_word_count >= min_words
        if body_ok:
            body_pass += 1

        print(f"  Language (Detected): {article.get('language', 'Unknown')} | Expected: {expected_lang}")
        print(f"  Title  : {title[:80]}...")
        print(f"  Title  [PASS]" if title_ok else f"  Title  [FAIL] (too short or empty)")
        print(f"  Body   : {body_word_count} words extracted")
        print(f"  Body   [PASS]" if body_ok else f"  Body   [FAIL] (expected >={min_words} words)")
        print()
    
    successful = total_tests - fetch_failures
    if successful == 0:
        print("All fetches failed. Check your internet connection.")
        return

    title_acc = (title_pass / total_tests) * 100
    body_acc = (body_pass / total_tests) * 100
    overall_acc = (title_acc + body_acc) / 2
    
    print("=" * 60)
    print("   EVALUATION RESULTS")
    print("=" * 60)
    print(f"  Total Sites Tested    : {total_tests}")
    print(f"  Fetch Failures        : {fetch_failures}")
    print(f"  Title Extraction Acc  : {title_acc:.1f}%")
    print(f"  Body Extraction Acc   : {body_acc:.1f}%")
    print(f"  Overall System Acc    : {overall_acc:.1f}%")
    print("=" * 60)
    
if __name__ == "__main__":
    evaluate_accuracy()
