import os
import time
import logging
from typing import Optional, List
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class Scraper:
    def __init__(self, timeout: int = 10, retries: int = 3):
        self.timeout = timeout
        self.retries = retries
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }

    def fetch_html(self, url: str) -> Optional[str]:
        for attempt in range(1, self.retries + 1):
            try:
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                response.encoding = response.apparent_encoding or 'utf-8'
                return response.text
            except requests.exceptions.RequestException as exc:
                logger.warning(f"Fetch attempt {attempt}/{self.retries} failed for {url}: {exc}")
                if attempt < self.retries:
                    time.sleep(1.5)

        logger.error(f"Failed to retrieve {url} after {self.retries} attempts.")
        return None

    def crawl_homepage(self, url: str, max_links: int = 10) -> List[str]:
        html = self.fetch_html(url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        base_domain = urlparse(url).netloc
        article_links = []

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            if href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue

            absolute_url = urljoin(url, href)
            parsed = urlparse(absolute_url)

            if parsed.netloc == base_domain and len(parsed.path) > 8:
                if absolute_url not in article_links:
                    article_links.append(absolute_url)

            if len(article_links) >= max_links:
                break

        return article_links

    def save_raw_html(self, html_content: str, filename: str, save_dir: str = 'data/raw'):
        if not html_content:
            return
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
        except IOError as exc:
            logger.error(f"Failed to save raw HTML to {filepath}: {exc}")
