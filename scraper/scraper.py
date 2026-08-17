import requests
import time
import logging
import os
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Scraper:
    def __init__(self, timeout: int = 10, retries: int = 3):
        self.timeout = timeout
        self.retries = retries
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
    def fetch_html(self, url: str) -> Optional[str]:
        """
        Fetches HTML from a given URL with retries and timeout handling.
        """
        attempt = 0
        while attempt < self.retries:
            try:
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                # Use apparent_encoding if encoding is not cleanly set, or force utf-8 for broad compatibility
                response.encoding = response.apparent_encoding or 'utf-8'
                return response.text
            except requests.exceptions.RequestException as e:
                attempt += 1
                logging.warning(f"Attempt {attempt}/{self.retries} failed for URL {url}: {e}")
                time.sleep(2) # Backoff before retry
                
        logging.error(f"Failed to fetch {url} after {self.retries} attempts.")
        return None

    def crawl_homepage(self, url: str, max_links: int = 10) -> List[str]:
        """
        Crawls a homepage and returns a list of absolute URLs for potential articles.
        """
        html = self.fetch_html(url)
        if not html:
            return []
            
        soup = BeautifulSoup(html, 'html.parser')
        base_domain = urlparse(url).netloc
        
        article_links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Ignore javascript, mailto, etc.
            if href.startswith(('javascript:', 'mailto:', 'tel:')):
                continue
                
            absolute_url = urljoin(url, href)
            parsed_url = urlparse(absolute_url)
            
            # Keep links from the same domain to avoid scraping random external sites
            if parsed_url.netloc == base_domain:
                # Basic heuristic: ignore very short paths (like '/') or purely query params
                if len(parsed_url.path) > 10: 
                    if absolute_url not in article_links:
                        article_links.append(absolute_url)
                        
            if len(article_links) >= max_links:
                break
                
        return article_links

    def save_raw_html(self, html_content: str, filename: str, save_dir: str = 'data/raw'):
        """
        Saves raw HTML content for auditing or further processing.
        """
        if not html_content:
            return
            
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
        except IOError as e:
            logging.error(f"Failed to save raw HTML to {filepath}: {e}")
