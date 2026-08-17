import re

class LanguageUtils:
    @staticmethod
    def detect_language(text: str) -> str:
        """
        Basic heuristic language detection for English, Arabic, and Russian.
        In a production system, this could use langdetect or similar.
        """
        # Arabic characters range
        if re.search(r'[\u0600-\u06FF]', text):
            return 'Arabic'
        
        # Cyrillic (Russian) characters range
        if re.search(r'[\u0400-\u04FF]', text):
            return 'Russian'
            
        # Default to English if predominantly Latin
        return 'English'

    @staticmethod
    def is_rtl(language: str) -> bool:
        """
        Returns True if the language is Right-to-Left (e.g., Arabic)
        """
        return language.lower() == 'arabic'
