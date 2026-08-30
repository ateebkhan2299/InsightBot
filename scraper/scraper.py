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

    def is_feed_content(self, content: str) -> bool:
        if not content:
            return False
        snippet = content[:1500].lower()
        return ('<rss' in snippet or '<feed' in snippet or '<channel' in snippet or
                '<rdf:rdf' in snippet or 'xmlns="http://www.w3.org/2005/atom"' in snippet or
                '<?xml' in snippet and ('<item' in snippet or '<entry' in snippet))

    def parse_feed_links(self, xml_content: str, base_url: str = "", max_links: int = 25) -> List[str]:
        if not xml_content:
            return []

        article_links = []

        # 1. Try ElementTree XML parsing first (standard library XML parser)
        try:
            import xml.etree.ElementTree as ET
            raw_bytes = xml_content.encode('utf-8') if isinstance(xml_content, str) else xml_content
            root = ET.fromstring(raw_bytes)

            # RSS items
            for item in root.iter('item'):
                link = None
                link_elem = item.find('link')
                if link_elem is not None and link_elem.text:
                    link = link_elem.text.strip()
                if not link:
                    guid_elem = item.find('guid')
                    if guid_elem is not None and guid_elem.text and guid_elem.text.strip().startswith('http'):
                        link = guid_elem.text.strip()
                if link and link.startswith('http'):
                    if base_url:
                        link = urljoin(base_url, link)
                    if link not in article_links:
                        article_links.append(link)
                if len(article_links) >= max_links:
                    return article_links

            # Atom entries (with or without namespace)
            for entry in list(root.iter('{http://www.w3.org/2005/Atom}entry')) + list(root.iter('entry')):
                link = None
                link_elem = entry.find('{http://www.w3.org/2005/Atom}link') or entry.find('link')
                if link_elem is not None:
                    link = link_elem.attrib.get('href') or (link_elem.text or '').strip()
                if not link:
                    id_elem = entry.find('{http://www.w3.org/2005/Atom}id') or entry.find('id')
                    if id_elem is not None and id_elem.text and id_elem.text.strip().startswith('http'):
                        link = id_elem.text.strip()
                if link and link.startswith('http'):
                    if base_url:
                        link = urljoin(base_url, link)
                    if link not in article_links:
                        article_links.append(link)
                if len(article_links) >= max_links:
                    return article_links

            if article_links:
                return article_links
        except Exception:
            pass

        # 2. Fallback to BeautifulSoup parser
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                soup = BeautifulSoup(xml_content, 'html.parser')

                # Check RSS <item> tags
                items = soup.find_all('item')
                if items:
                    for item in items:
                        link_tag = item.find('link')
                        link = None
                        if link_tag:
                            link = (link_tag.text or link_tag.get('href') or '').strip()
                            if not link and link_tag.next_sibling:
                                link = str(link_tag.next_sibling).strip()
                        if not link:
                            guid_tag = item.find('guid')
                            if guid_tag and guid_tag.text and guid_tag.text.startswith('http'):
                                link = guid_tag.text.strip()

                        if link and link.startswith('http'):
                            if base_url:
                                link = urljoin(base_url, link)
                            if link not in article_links:
                                article_links.append(link)
                        if len(article_links) >= max_links:
                            break

                # Check Atom <entry> tags
                if not article_links:
                    entries = soup.find_all('entry')
                    for entry in entries:
                        link_tag = entry.find('link')
                        link = None
                        if link_tag:
                            link = link_tag.get('href') or link_tag.text.strip()
                        if not link:
                            id_tag = entry.find('id')
                            if id_tag and id_tag.text and id_tag.text.startswith('http'):
                                link = id_tag.text.strip()

                        if link and link.startswith('http'):
                            if base_url:
                                link = urljoin(base_url, link)
                            if link not in article_links:
                                article_links.append(link)
                        if len(article_links) >= max_links:
                            break
        except Exception as exc:
            logger.warning(f"Feed parsing error: {exc}")

        return article_links

    def crawl_homepage(self, url: str, max_links: int = 15) -> List[str]:
        return self.crawl_source(url, max_links=max_links)

    def crawl_source(self, url: str, max_links: int = 15) -> List[str]:
        html = self.fetch_html(url)
        if not html:
            return []

        # 1. Check if the target is an RSS / Atom feed
        if self.is_feed_content(html):
            feed_links = self.parse_feed_links(html, base_url=url, max_links=max_links)
            if feed_links:
                return feed_links

        # 2. Otherwise parse HTML web page
        soup = BeautifulSoup(html, 'html.parser')
        base_domain = urlparse(url).netloc.replace("www.", "")
        article_links = []

        # Check if the HTML links to an RSS feed
        rss_link_tag = soup.find('link', type=lambda t: t and ('rss' in t or 'atom' in t))
        if rss_link_tag and rss_link_tag.get('href'):
            rss_url = urljoin(url, rss_link_tag['href'])
            try:
                rss_html = self.fetch_html(rss_url)
                if rss_html and self.is_feed_content(rss_html):
                    feed_links = self.parse_feed_links(rss_html, base_url=rss_url, max_links=max_links)
                    if feed_links:
                        return feed_links
            except Exception:
                pass

        # Discover article links from HTML <a> tags
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#', 'whatsapp:')):
                continue

            absolute_url = urljoin(url, href)
            parsed = urlparse(absolute_url)
            domain = parsed.netloc.replace("www.", "")

            # Filter out non-article URLs (login, tags, categories, search, home)
            path_lower = parsed.path.lower()
            if domain == base_domain and len(parsed.path) > 8:
                skip_patterns = [
                    '/tag/', '/category/', '/author/', '/page/', '/search',
                    '/login', '/register', '/privacy', '/terms', '/about',
                    '/contact', '/advertise', '/sitemap', '.jpg', '.png', '.pdf'
                ]
                if any(sp in path_lower for sp in skip_patterns):
                    continue

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
