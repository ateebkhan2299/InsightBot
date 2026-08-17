import re
from bs4 import BeautifulSoup, Comment

class HTMLCleaner:
    @staticmethod
    def clean_html(raw_html: str) -> BeautifulSoup:
        """
        Parses raw HTML, removes unnecessary tags (scripts, styles, ads),
        and returns a cleaned BeautifulSoup object.
        """
        soup = BeautifulSoup(raw_html, 'html.parser')
        
        # Remove script and style tags
        for element in soup(["script", "style", "noscript", "iframe", "nav", "footer", "header", "aside"]):
            element.decompose()
            
        # Remove comments
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            comment.extract()
            
        # Remove known ad containers (basic heuristics)
        ad_classes = re.compile(r'ad-|promo|sponsor|advert', re.I)
        for ad in soup.find_all(class_=ad_classes):
            ad.decompose()
            
        return soup

    @staticmethod
    def get_text_from_element(element) -> str:
        """
        Extracts and normalizes text from a BeautifulSoup element.
        """
        if not element:
            return ""
        text = element.get_text(separator=' ')
        return HTMLCleaner.normalize_whitespace(text)
        
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        Cleans up excessive whitespace and normalizes it.
        """
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
