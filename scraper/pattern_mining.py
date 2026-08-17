"""
InsightBot - Pattern Mining Engine
===================================
SRS Requirement (Section 1.6, Point iii):
"Pattern-Based Content Extraction - The system shall identify article titles
and bodies using predefined structural patterns. These patterns include detecting
the largest text blocks for headlines and the longest paragraph elements for
article bodies, based on analysis from training websites."

This module implements the TRAINING phase of InsightBot:
- Analyzes HTML from 40 training websites
- Counts frequency of structural patterns (h1 classes, article containers, etc.)
- Identifies which CSS selectors most commonly contain titles and bodies
- Saves learned rules to models/extraction_rules.json

The saved rules are then loaded by ArticleExtractor at runtime for TESTING.
"""

import json
import os
from bs4 import BeautifulSoup
from collections import Counter
import re
import logging

logger = logging.getLogger(__name__)


class PatternMiner:
    """
    Mines structural DOM patterns from a corpus of HTML pages.
    
    Training Phase:  mine_patterns(html_list) → learns selectors → saves to JSON
    Testing Phase:   _load_rules()           → loads saved selectors from JSON
    """
    
    # Baseline rules always included (language-agnostic universal selectors)
    BASELINE_TITLE_SELECTORS = [
        "h1", "h1.title", "h1.headline", "h1.article-title",
        "h1.entry-title", "h2.title", "div.article-title",
        "meta[property='og:title']"
    ]
    BASELINE_BODY_SELECTORS = [
        "article", "main", "div.article-body", "div.content",
        "div.post-content", "div.entry-content", "div.story-body",
        "section.article-content"
    ]
    BASELINE_DATE_SELECTORS = [
        "time", "time[datetime]", "span.date", "span.published",
        "div.publication-date", "meta[property='article:published_time']",
        "meta[name='pubdate']"
    ]

    def __init__(self, rules_file_path: str = 'models/extraction_rules.json'):
        self.rules_file_path = rules_file_path
        self.rules = self._load_rules()

    def _load_rules(self) -> dict:
        """
        Load mined rules from JSON file if it exists.
        Falls back to baseline universal selectors if no training has been done yet.
        """
        if os.path.exists(self.rules_file_path):
            try:
                with open(self.rules_file_path, 'r', encoding='utf-8') as f:
                    rules = json.load(f)
                    logger.info(f"Loaded mined rules from {self.rules_file_path}")
                    return rules
            except Exception as e:
                logger.warning(f"Could not load rules file: {e}. Using baseline rules.")
        
        # No training done yet — use universal baseline
        logger.info("No mined rules found. Using baseline selectors.")
        return {
            "title_selectors": self.BASELINE_TITLE_SELECTORS.copy(),
            "body_selectors":  self.BASELINE_BODY_SELECTORS.copy(),
            "date_selectors":  self.BASELINE_DATE_SELECTORS.copy(),
            "training_stats":  {"pages_trained": 0, "trained_at": None}
        }

    def save_rules(self):
        """Save current rules to JSON file."""
        os.makedirs(os.path.dirname(self.rules_file_path), exist_ok=True)
        with open(self.rules_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.rules, f, indent=4, ensure_ascii=False)
        logger.info(f"Rules saved to {self.rules_file_path}")

    def mine_patterns(self, html_contents: list) -> dict:
        """
        Core Training Phase — analyzes real HTML from 40 training websites.
        
        Strategy (as per SRS Section 1.2):
        - Title Mining  : Count frequency of h1/h2 tags and their CSS classes.
                          The most common selector across training sites = best rule.
        - Body Mining   : Find the container (div/article/main/section) with the
                          highest density of <p> tags in each page.
                          The most common selector = best body container rule.
        - Date Mining   : Look for <time>, <span> with date-like classes, and
                          Open Graph meta tags for publication date.
        
        Args:
            html_contents: List of raw HTML strings from training websites
            
        Returns:
            dict: Updated rules dict with mined selectors merged with baseline
        """
        import datetime
        
        title_counter = Counter()
        body_counter  = Counter()
        date_counter  = Counter()
        
        logger.info(f"Mining patterns from {len(html_contents)} HTML pages...")
        
        for i, html in enumerate(html_contents):
            try:
                soup = BeautifulSoup(html, 'html.parser')
                
                # ── TITLE MINING ────────────────────────────────────────────
                # Rule: h1 tags carry the article headline.
                # We record both plain "h1" and "h1.classname" variants.
                # The most frequent selector across all 40 sites becomes a rule.
                h1_tags = soup.find_all('h1')
                if h1_tags:
                    # Pick the h1 with the most text (likely the main headline)
                    best_h1 = max(h1_tags, key=lambda t: len(t.get_text()))
                    classes = best_h1.get('class', [])
                    if classes:
                        # Record specific selector e.g. "h1.article-title"
                        for cls in classes[:2]:  # Max 2 classes
                            title_counter[f"h1.{cls}"] += 1
                    title_counter["h1"] += 1  # Always count plain h1
                else:
                    # Fallback: check h2
                    h2_tags = soup.find_all('h2')
                    if h2_tags:
                        title_counter["h2"] += 1

                # Also check Open Graph meta title (very common in news sites)
                og_title = soup.find('meta', property='og:title')
                if og_title:
                    title_counter["meta[property='og:title']"] += 1
                
                # ── BODY MINING ─────────────────────────────────────────────
                # Rule: The container with the highest density of <p> tags
                # that have substantial text is the article body.
                best_container = None
                best_score = 0
                
                for container in soup.find_all(['article', 'main', 'div', 'section']):
                    # Count meaningful paragraphs (>40 chars = real sentences)
                    meaningful_p = [
                        p for p in container.find_all('p')
                        if len(p.get_text().strip()) > 40
                    ]
                    score = sum(len(p.get_text().strip()) for p in meaningful_p)
                    
                    if score > best_score:
                        best_score = score
                        best_container = container
                
                if best_container and best_score > 200:
                    tag_name = best_container.name
                    classes  = best_container.get('class', [])
                    if classes:
                        # Record specific selector e.g. "div.article-body"
                        for cls in classes[:2]:
                            selector = f"{tag_name}.{cls}"
                            # Only record if it looks like a content class
                            if any(kw in cls.lower() for kw in [
                                'article', 'content', 'body', 'story', 'post',
                                'text', 'entry', 'main', 'news'
                            ]):
                                body_counter[selector] += 1
                    # Always record the plain tag name too
                    body_counter[tag_name] += 1
                
                # ── DATE MINING ──────────────────────────────────────────────
                # Look for <time> tags and publication meta tags
                time_tag = soup.find('time')
                if time_tag:
                    date_counter["time"] += 1
                    if time_tag.get('datetime'):
                        date_counter["time[datetime]"] += 1
                
                og_date = soup.find('meta', property='article:published_time')
                if og_date:
                    date_counter["meta[property='article:published_time']"] += 1
                    
                # Common date span classes
                for span in soup.find_all('span'):
                    cls = ' '.join(span.get('class', []))
                    if any(kw in cls.lower() for kw in ['date', 'publish', 'time']):
                        date_counter[f"span.{span.get('class', ['date'])[0]}"] += 1
                        break
                        
            except Exception as e:
                logger.warning(f"Error mining page {i+1}: {e}")
                continue
        
        # ── MERGE MINED RULES WITH BASELINE ──────────────────────────────
        # Start from baseline, then prepend the top mined selectors
        # (mined selectors go first = higher priority during extraction)
        
        # Get top N selectors from mining (must appear in at least 2 pages)
        MIN_FREQUENCY = max(1, len(html_contents) // 10)  # at least 10% of pages
        
        top_title_selectors = [
            sel for sel, count in title_counter.most_common(8)
            if count >= MIN_FREQUENCY
        ]
        top_body_selectors = [
            sel for sel, count in body_counter.most_common(8)
            if count >= MIN_FREQUENCY
        ]
        top_date_selectors = [
            sel for sel, count in date_counter.most_common(5)
            if count >= MIN_FREQUENCY
        ]
        
        # Build final rules: mined first (higher priority), then baseline (fallback)
        def merge_unique(mined: list, baseline: list) -> list:
            seen = set()
            result = []
            for item in mined + baseline:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
            return result
        
        self.rules = {
            "title_selectors": merge_unique(top_title_selectors, self.BASELINE_TITLE_SELECTORS),
            "body_selectors":  merge_unique(top_body_selectors,  self.BASELINE_BODY_SELECTORS),
            "date_selectors":  merge_unique(top_date_selectors,  self.BASELINE_DATE_SELECTORS),
            "training_stats": {
                "pages_trained": len(html_contents),
                "trained_at": datetime.datetime.utcnow().isoformat(),
                "title_frequencies": dict(title_counter.most_common(10)),
                "body_frequencies":  dict(body_counter.most_common(10)),
            }
        }
        
        self.save_rules()
        logger.info(f"Pattern mining complete. Rules saved.")
        return self.rules
