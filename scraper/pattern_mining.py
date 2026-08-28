import json
import os
import re
import logging
import datetime
from collections import Counter
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class PatternMiner:
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
        if os.path.exists(self.rules_file_path):
            try:
                with open(self.rules_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as exc:
                logger.warning(f"Could not load rules from {self.rules_file_path}: {exc}")

        return {
            "title_selectors": self.BASELINE_TITLE_SELECTORS.copy(),
            "body_selectors": self.BASELINE_BODY_SELECTORS.copy(),
            "date_selectors": self.BASELINE_DATE_SELECTORS.copy(),
            "training_stats": {"pages_trained": 0, "trained_at": None}
        }

    def save_rules(self):
        os.makedirs(os.path.dirname(self.rules_file_path), exist_ok=True)
        with open(self.rules_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.rules, f, indent=4, ensure_ascii=False)

    def mine_patterns(self, html_contents: list) -> dict:
        title_counter = Counter()
        body_counter = Counter()
        date_counter = Counter()

        for html in html_contents:
            try:
                soup = BeautifulSoup(html, 'html.parser')

                h1_tags = soup.find_all('h1')
                if h1_tags:
                    best_h1 = max(h1_tags, key=lambda t: len(t.get_text()))
                    classes = best_h1.get('class', [])
                    if classes:
                        for cls in classes[:2]:
                            title_counter[f"h1.{cls}"] += 1
                    title_counter["h1"] += 1
                else:
                    h2_tags = soup.find_all('h2')
                    if h2_tags:
                        title_counter["h2"] += 1

                og_title = soup.find('meta', property='og:title')
                if og_title:
                    title_counter["meta[property='og:title']"] += 1

                best_container = None
                best_score = 0

                for container in soup.find_all(['article', 'main', 'div', 'section']):
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
                    classes = best_container.get('class', [])
                    if classes:
                        for cls in classes[:2]:
                            if any(kw in cls.lower() for kw in [
                                'article', 'content', 'body', 'story', 'post',
                                'text', 'entry', 'main', 'news'
                            ]):
                                body_counter[f"{tag_name}.{cls}"] += 1
                    body_counter[tag_name] += 1

                time_tag = soup.find('time')
                if time_tag:
                    date_counter["time"] += 1
                    if time_tag.get('datetime'):
                        date_counter["time[datetime]"] += 1

                og_date = soup.find('meta', property='article:published_time')
                if og_date:
                    date_counter["meta[property='article:published_time']"] += 1

                for span in soup.find_all('span'):
                    cls_list = span.get('class', [])
                    cls = ' '.join(cls_list)
                    if any(kw in cls.lower() for kw in ['date', 'publish', 'time']) and cls_list:
                        date_counter[f"span.{cls_list[0]}"] += 1
                        break

            except Exception:
                continue

        min_freq = max(1, len(html_contents) // 10)

        top_title = [sel for sel, count in title_counter.most_common(8) if count >= min_freq]
        top_body = [sel for sel, count in body_counter.most_common(8) if count >= min_freq]
        top_date = [sel for sel, count in date_counter.most_common(5) if count >= min_freq]

        def merge_unique(mined: list, baseline: list) -> list:
            seen = set()
            result = []
            for item in mined + baseline:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
            return result

        self.rules = {
            "title_selectors": merge_unique(top_title, self.BASELINE_TITLE_SELECTORS),
            "body_selectors": merge_unique(top_body, self.BASELINE_BODY_SELECTORS),
            "date_selectors": merge_unique(top_date, self.BASELINE_DATE_SELECTORS),
            "training_stats": {
                "pages_trained": len(html_contents),
                "trained_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "title_frequencies": dict(title_counter.most_common(10)),
                "body_frequencies": dict(body_counter.most_common(10)),
            }
        }

        self.save_rules()
        return self.rules
