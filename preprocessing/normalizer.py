import re

class TextNormalizer:
    @staticmethod
    def normalize(text: str) -> str:
        """
        Applies additional normalization beyond whitespace cleaning.
        Ensures Unicode correctness.
        """
        if not text:
            return ""
            
        # Remove non-printable characters except spaces
        text = ''.join(c for c in text if c.isprintable() or c in [' ', '\n', '\t'])
        
        # Collapse multiple newlines if any
        text = re.sub(r'\n+', '\n', text)
        
        return text.strip()
