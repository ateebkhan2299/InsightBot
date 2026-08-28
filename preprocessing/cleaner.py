import re
from bs4 import BeautifulSoup, Comment


class HTMLCleaner:
    @staticmethod
    def clean_html(raw_html: str) -> BeautifulSoup:
        soup = BeautifulSoup(raw_html, 'html.parser')

        for element in soup(["script", "style", "noscript", "iframe", "nav", "footer", "header", "aside"]):
            element.decompose()

        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            comment.extract()

        ad_classes = re.compile(r'ad-|promo|sponsor|advert', re.I)
        for ad in soup.find_all(class_=ad_classes):
            ad.decompose()

        return soup

    @staticmethod
    def get_text_from_element(element) -> str:
        if not element:
            return ""
        text = element.get_text(separator=' ')
        return HTMLCleaner.normalize_whitespace(text)

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()
