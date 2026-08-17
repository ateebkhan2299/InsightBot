from bs4 import BeautifulSoup
import re
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from .pattern_mining import PatternMiner
from preprocessing.cleaner import HTMLCleaner
from preprocessing.normalizer import TextNormalizer
from preprocessing.language_utils import LanguageUtils

class ArticleExtractor:
    def __init__(self, miner: PatternMiner = None):
        self.miner = miner or PatternMiner()
        self.cleaner = HTMLCleaner()
        self.normalizer = TextNormalizer()

    def extract(self, raw_html: str, source_url: str = "") -> Dict[str, Any]:
        """
        Extracts structured data from raw HTML using pattern-based rules.
        """
        soup = self.cleaner.clean_html(raw_html)
        
        title = self._extract_title(soup)
        body = self._extract_body(soup)
        date = self._extract_date(soup)
        
        # Normalize extracted text
        title = self.normalizer.normalize(title)
        body = self.normalizer.normalize(body)
        
        # Detect language
        language = LanguageUtils.detect_language(body) if body else "Unknown"

        return {
            "title": title,
            "body": body,
            "publication_date": date,
            "language": language,
            "source_url": source_url,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "extraction_method": "pattern-based"
        }

    def _extract_title(self, soup: BeautifulSoup) -> str:
        for selector in self.miner.rules.get("title_selectors", []):
            elements = soup.select(selector)
            if elements:
                # Open Graph title selectors target a <meta> tag, whose text is
                # empty. Use its content attribute before considering tag text.
                if selector.startswith("meta"):
                    for element in elements:
                        content = element.get("content", "").strip()
                        if len(content) > 5:
                            return content
                # Prefer the shortest valid text if multiple matches (usually the purest title)
                texts = [e.get_text().strip() for e in elements if len(e.get_text().strip()) > 5]
                if texts:
                    return texts[0]
                    
        # Fallback: find any h1 or title tag
        fallback = soup.find(['h1', 'title'])
        return fallback.get_text().strip() if fallback else "Unknown Title"

    def _extract_body(self, soup: BeautifulSoup) -> str:
        """
        Layered body extraction strategy (SRS Pattern-Mining approach):
        Layer 1: Semantic HTML tags (article, main, [role=main]) 
        Layer 2: Rule-based selectors from pattern_mining rules
        Layer 3: Paragraph-density analysis - find container with most <p> text
        Layer 4: Largest div fallback
        """
        
        # Layer 1: Try semantic HTML5 tags first (most reliable signal)
        for semantic_tag in ['article', 'main', '[role="main"]', '[role="article"]']:
            elements = soup.select(semantic_tag)
            if elements:
                all_p = []
                for el in elements:
                    for p in el.find_all('p'):
                        t = p.get_text().strip()
                        if len(t) > 30:  # filter out nav items / short labels
                            all_p.append(t)
                if len(all_p) >= 2:
                    return "\n\n".join(all_p)

        # Layer 2: Rule-based selectors from pattern_mining
        for selector in self.miner.rules.get("body_selectors", []):
            elements = soup.select(selector)
            if elements:
                extracted_text = []
                for element in elements:
                    paragraphs = element.find_all('p')
                    if paragraphs:
                        for p in paragraphs:
                            text = p.get_text().strip()
                            if len(text) > 30:
                                extracted_text.append(text)
                    else:
                        text = element.get_text(separator='\n').strip()
                        if len(text) > 50:
                            extracted_text.append(text)
                if extracted_text:
                    return "\n\n".join(extracted_text)

        # Layer 3: Paragraph-Density Analysis across ALL containers
        # This is the core SRS "pattern mining" heuristic:
        # The container with the highest density of meaningful <p> tags = article body
        best_container = None
        best_score = 0
        for container in soup.find_all(['div', 'section', 'article', 'main']):
            paragraphs = container.find_all('p', recursive=False)
            if not paragraphs:
                paragraphs = container.find_all('p')
            score = sum(len(p.get_text().strip()) for p in paragraphs if len(p.get_text().strip()) > 30)
            if score > best_score:
                best_score = score
                best_container = container

        if best_container and best_score > 100:
            texts = [p.get_text().strip() for p in best_container.find_all('p') if len(p.get_text().strip()) > 30]
            if texts:
                return "\n\n".join(texts)

        # Layer 4: Last resort — biggest text block in any div
        all_divs = soup.find_all('div')
        best_div = None
        max_length = 0
        for div in all_divs:
            text = div.get_text(separator=' ').strip()
            if len(text) > max_length:
                max_length = len(text)
                best_div = div

        return best_div.get_text(separator='\n').strip() if best_div else ""

    def _extract_date(self, soup: BeautifulSoup) -> str:
        for selector in self.miner.rules.get("date_selectors", []):
            if selector.startswith('meta'):
                # Handle meta tags differently
                prop_match = re.search(r"property='([^']+)'", selector)
                if prop_match:
                    meta = soup.find('meta', property=prop_match.group(1))
                    if meta and meta.get('content'):
                        return meta.get('content')
            else:
                elements = soup.select(selector)
                if elements:
                    return elements[0].get_text().strip()
        
        # Fallback generic date regex on entire html or head might be too slow.
        return ""
