import re


class LanguageUtils:
    @staticmethod
    def detect_language(text: str) -> str:
        if not text:
            return 'English'
        if re.search(r'[\u0600-\u06FF]', text):
            return 'Arabic'
        if re.search(r'[\u0400-\u04FF]', text):
            return 'Russian'
        return 'English'

    @staticmethod
    def is_rtl(language: str) -> bool:
        return (language or '').lower() == 'arabic'
